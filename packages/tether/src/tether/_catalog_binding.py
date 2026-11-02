"""Seal an explicit run-only policy decision around the frozen engine.

Raw originals and their pinned receipts stay external. Receipt copies retained
here are policy evidence; the frozen engine still reads original receipt paths.
This boundary checks stability, not exclusive ownership of the filesystem.
"""
from dataclasses import dataclass
from pathlib import Path
import re
import time

from asof.atomic import publish_bytes
from asof.chrono import load_snapshot
from asof.contracts import Case, Snapshot
from asof.serde import ContractError, canonical, decode, encode, fingerprint, parse_json
from asof.study.stable_read import checked_path, hash_file, read_file

from ._catalog_policy import (authorize_snapshot, reconcile_receipt, strict_json, validate_policy,
                              validate_source_catalog)

POLICY_DIR = "catalog-policy"
CONTROL_LIMIT = 16 * 1024 * 1024
PACKET_LIMIT = 64 * 1024 * 1024
PREPARATION_SECONDS = 300
METHOD = "tether.sealed_catalog_binding.v1"


def need(condition, message):
    if not condition:
        raise ContractError("TETHER sealed policy: " + message)


@dataclass(frozen=True)
class PolicyRequest:
    policy_path: Path
    roots_path: Path
    case_path: Path
    snapshot_path: Path
    catalog_path: Path
    use_id: str
    frame_sha256: str

    def validate(self):
        need(type(self.use_id) is str and bool(self.use_id.strip()), "explicit use ID required")
        need(type(self.frame_sha256) is str and re.fullmatch(r"[0-9a-f]{64}", self.frame_sha256),
             "independently selected frame SHA-256 required")


def _read(path, deadline, maximum=CONTROL_LIMIT):
    return read_file(Path(path), deadline, maximum)


def _json(path, deadline):
    return strict_json(_read(path, deadline))


def _descriptor(relative, payload):
    import hashlib
    return dict(path=relative, sha256=hashlib.sha256(payload).hexdigest(), bytes=len(payload))


def _publish(output, relative, payload, deadline, *, shared=False):
    destination = output.joinpath(*relative.split("/"))
    if shared and destination.exists():
        need(_read(destination, deadline, max(CONTROL_LIMIT, len(payload))) == payload,
             "conflicting immutable receipt/copy destination")
    else:
        publish_bytes(destination, payload)
    need(_read(destination, deadline, max(CONTROL_LIMIT, len(payload))) == payload,
         "published copy differs")
    return _descriptor(relative, payload)


def _roots(document):
    need(type(document) is dict and set(document) == {"schema_version", "roots"}
         and type(document["schema_version"]) is int and document["schema_version"] == 1
         and type(document["roots"]) is dict, "root mapping must be schema 1 with roots")
    for value in document["roots"].values():
        need(type(value) is str and Path(value).is_absolute() and not Path(value).drive.startswith("\\\\"),
             "roots must be absolute local paths")
    need("metadata" in document["roots"], "explicit metadata root required for retained provenance")
    return document["roots"]


def _selected_use(policy, use_id):
    rows = [u for u in policy["uses"] if u["use_id"] == use_id]
    need(len(rows) == 1, "unknown/ambiguous use")
    return rows[0]


def _decision(policy, snapshot, case, roots, use_id, frame):
    need(snapshot.get("profile") != "synthetic_demo", "Synthetic demo profile bypasses the frozen catalog; unsupported for artifact-policy execution")
    result = authorize_snapshot(policy, snapshot, case=case, use_id=use_id, root_aliases=roots)
    need(result["binding"]["frame_sha256"] == frame, "selected frame differs from use")
    # Strict engine decoding is additional to exact policy metadata comparison.
    decode(Case, case).validate()
    decode(Snapshot, snapshot)
    identities = [row["physical_path"].replace("\\", "/").casefold()
                  for row in result["binding"]["inventory"]]
    need(len(identities) == len(set(identities)), "physical artifact path aliases")
    use = _selected_use(policy, use_id)
    need(all(row["relative_path"].casefold() != "snapshot.json" for row in result["binding"]["inventory"]
             if row["root_alias"] == use["snapshot_root_alias"]), "copied input collides with snapshot control")
    return result


def _check_hash(path, expected, deadline):
    observed = hash_file(path, deadline)
    need(observed["sha256"] == expected["sha256"] and observed["bytes"] == expected["bytes"],
         "source hash/size differs: " + str(path))


def _check_receipt(entry, roots, payload, deadline):
    reference = entry["receipt"]
    receipt = strict_json(payload)
    reconcile_receipt(dict(receipt_id=reference["receipt_id"], dataset_id=entry["dataset_id"],
                           release_id=entry["release_id"], url=reference["url"],
                           relative_path=entry["relative_path"], expected_sha256=entry["sha256"]),
                      receipt, observed_size=entry["bytes"], observed_sha256=entry["sha256"])
    source = checked_path(Path(roots[entry["root_alias"]]), entry["relative_path"])
    need(str(source) == entry["physical_path"], "receipt physical source binding differs")


def _metadata_proofs(output, policy, decision, roots, deadline, *, publish):
    records = {row["artifact_id"]: row for row in policy["artifacts"]}
    proofs = []
    for entry in decision["binding"]["inventory"]:
        for reference in records[entry["artifact_id"]]["provenance"]["evidence"]:
            relative = POLICY_DIR + "/provenance/" + reference["sha256"] + ".bin"
            if publish:
                path = checked_path(Path(roots["metadata"]), reference["path"])
            else:
                path = checked_path(output, relative)
            payload = _read(path, deadline)
            need(_descriptor("", payload)["sha256"] == reference["sha256"], "retained provenance hash differs")
            if publish:
                _publish(output, relative, payload, deadline, shared=True)
            proofs.append(dict(source_id=entry["source_id"], declared_path=reference["path"],
                               **_descriptor(relative, payload)))
    return proofs


def prepare_policy_run(output, request):
    """Called after exclusive outer reservation, before any backend dispatch."""
    request.validate()
    output = Path(output).absolute()
    deadline = time.monotonic() + PREPARATION_SECONDS
    originals = {"policy": Path(request.policy_path).absolute(), "roots": Path(request.roots_path).absolute(),
                 "case": Path(request.case_path).absolute(), "snapshot": Path(request.snapshot_path).absolute(),
                 "source_catalog": Path(request.catalog_path).absolute()}
    raw = {name: _read(path, deadline) for name, path in originals.items()}
    documents = {name: strict_json(payload) for name, payload in raw.items()}
    policy = validate_policy(documents["policy"])
    validate_source_catalog(policy, raw["source_catalog"])
    roots = _roots(documents["roots"])
    source_catalog = checked_path(Path(roots["metadata"]), policy["source_catalog"]["path"])
    need(str(source_catalog) == str(originals["source_catalog"]), "schema-one catalog path differs from metadata root")
    case, snapshot = documents["case"], documents["snapshot"]
    decision = _decision(policy, snapshot, case, roots, request.use_id, request.frame_sha256)
    use = _selected_use(policy, request.use_id)
    need(str(originals["snapshot"].parent) == str(Path(roots[use["snapshot_root_alias"]])),
         "selected snapshot root differs from actual input location")
    controls = {name: _publish(output, POLICY_DIR + "/" + name + ".json", payload, deadline)
                for name, payload in raw.items()}
    controls["projection"] = _publish(output, POLICY_DIR + "/projection.json",
                                       canonical(decision["projection"]) + b"\n", deadline)
    controls["decision"] = _publish(output, POLICY_DIR + "/decision.json",
                                     canonical(decision["binding"]) + b"\n", deadline)
    metadata_proofs = _metadata_proofs(output, policy, decision, roots, deadline, publish=True)
    copied, receipts, external = [], [], []
    copied_names = {"snapshot.json"}
    for entry in decision["binding"]["inventory"]:
        original = checked_path(Path(roots[entry["root_alias"]]), entry["relative_path"])
        need(str(original) == entry["physical_path"], "physical path differs from authorized identity")
        if entry["root_alias"] == use["snapshot_root_alias"]:
            name = entry["relative_path"].casefold()
            need(name not in copied_names, "copied input path collides with snapshot/control")
            copied_names.add(name)
            payload = _read(original, deadline, PACKET_LIMIT)
            descriptor = _descriptor("", payload)
            need(descriptor["sha256"] == entry["sha256"] and descriptor["bytes"] == entry["bytes"],
                 "normalized packet/mapping differs")
            copied.append(dict(source_id=entry["source_id"], **_publish(output,
                POLICY_DIR + "/inputs/" + entry["relative_path"], payload, deadline)))
        else:
            _check_hash(original, entry, deadline)
            external.append(dict(source_id=entry["source_id"], path=str(original),
                                 sha256=entry["sha256"], bytes=entry["bytes"]))
        if entry["receipt"] is not None:
            ref = entry["receipt"]
            receipt_path = checked_path(Path(roots[ref["root_alias"]]), ref["relative_path"])
            payload = _read(receipt_path, deadline)
            need(_descriptor("", payload)["sha256"] == ref["sha256"], "original receipt hash differs")
            _check_receipt(entry, roots, payload, deadline)
            receipts.append(dict(source_id=entry["source_id"], original_path=str(receipt_path),
                **_publish(output, POLICY_DIR + "/receipts/" + ref["sha256"] + ".json", payload,
                           deadline, shared=True)))
    controls["execution_snapshot"] = _publish(output, POLICY_DIR + "/inputs/snapshot.json", raw["snapshot"], deadline)
    seal = dict(schema_version=1, method=METHOD, use_id=request.use_id, frame_sha256=request.frame_sha256,
                original_control_paths={name: str(path) for name, path in originals.items()},
                controls=controls, copies=copied, external_sources=external, receipts=receipts,
                metadata_proofs=metadata_proofs,
                execution=dict(case=controls["case"]["path"], snapshot=controls["execution_snapshot"]["path"],
                               catalog=controls["projection"]["path"]),
                receipt_execution="original_pinned_paths_rechecked_against_archived_copies",
                scientific_validation="not_established")
    seal_descriptor = _publish(output, POLICY_DIR + "/binding.json", canonical(seal) + b"\n", deadline)
    # Repeat admission against the actual copied controls; this parses eligible
    # packets and publication dates before dispatch, without constructing a backend.
    verify_policy_run(output, seal_descriptor, check_engine=False)
    return seal_descriptor


def policy_engine_args(output, argv, descriptor):
    deadline = time.monotonic() + PREPARATION_SECONDS
    seal = _json(checked_path(Path(output), descriptor["path"]), deadline)
    result, index = [], 0
    remove = {"--case", "--snapshot", "--catalog", "--catalog-policy", "--policy-use",
              "--policy-roots", "--policy-frame-sha256"}
    while index < len(argv):
        token = argv[index]
        if token in remove:
            index += 2
        elif token.split("=", 1)[0] in remove:
            index += 1
        else:
            result.append(token)
            index += 1
    for key in ("case", "snapshot", "catalog"):
        result += ["--" + key, str(checked_path(Path(output), seal["execution"][key]))]
    return result


def verify_policy_run(output, descriptor, *, check_engine=True):
    """Reconstruct from copied controls; originals remain required for raw proof."""
    output = Path(output).absolute()
    deadline = time.monotonic() + PREPARATION_SECONDS
    need(type(descriptor) is dict and set(descriptor) == {"path", "sha256", "bytes"}
         and descriptor["path"] == POLICY_DIR + "/binding.json", "binding descriptor differs")
    payload = _read(checked_path(output, descriptor["path"]), deadline)
    need(canonical(_descriptor(descriptor["path"], payload)) == canonical(descriptor), "binding hash/bytes differ")
    seal = strict_json(payload)
    need(set(seal) == {"schema_version", "method", "use_id", "frame_sha256", "original_control_paths",
                      "controls", "copies", "external_sources", "receipts", "execution",
                      "receipt_execution", "scientific_validation", "metadata_proofs"}
         and type(seal["schema_version"]) is int and seal["schema_version"] == 1 and seal["method"] == METHOD
         and seal["scientific_validation"] == "not_established"
         and seal["receipt_execution"] == "original_pinned_paths_rechecked_against_archived_copies",
         "invalid binding envelope")
    need(set(seal["controls"]) == {"policy", "roots", "case", "snapshot", "projection", "decision", "execution_snapshot", "source_catalog"},
         "control inventory differs")
    controls, raw_controls = {}, {}
    for name, proof in seal["controls"].items():
        expected = POLICY_DIR + ("/inputs/snapshot.json" if name == "execution_snapshot" else "/" + name + ".json")
        need(proof["path"] == expected, "control path differs")
        payload = _read(checked_path(output, proof["path"]), deadline)
        need(canonical(_descriptor(proof["path"], payload)) == canonical(proof), "control hash/bytes differ")
        controls[name] = strict_json(payload)
        raw_controls[name] = payload
    need(raw_controls["snapshot"] == raw_controls["execution_snapshot"], "executed snapshot bytes differ")
    validate_source_catalog(controls["policy"], raw_controls["source_catalog"])
    roots = _roots(controls["roots"])
    need(str(Path(roots["metadata"]).joinpath(*controls["policy"]["source_catalog"]["path"].split("/"))) ==
         seal["original_control_paths"]["source_catalog"], "original source catalog location differs")
    decision = _decision(controls["policy"], controls["snapshot"], controls["case"], roots,
                         seal["use_id"], seal["frame_sha256"])
    need(canonical(decision["binding"]) == canonical(controls["decision"]), "policy decision differs")
    need(canonical(decision["projection"]) == canonical(controls["projection"]), "policy projection differs")
    need(canonical(seal["metadata_proofs"]) == canonical(_metadata_proofs(output, controls["policy"],
         decision, roots, deadline, publish=False)), "retained provenance inventory differs")
    use = _selected_use(controls["policy"], seal["use_id"])
    need(str(Path(seal["original_control_paths"]["snapshot"]).parent) ==
         str(Path(roots[use["snapshot_root_alias"]])), "original snapshot location differs")
    expected_copies, expected_external, expected_receipts = [], [], []
    for entry in decision["binding"]["inventory"]:
        if entry["root_alias"] == use["snapshot_root_alias"]:
            relative = POLICY_DIR + "/inputs/" + entry["relative_path"]
            proof = dict(source_id=entry["source_id"], path=relative, sha256=entry["sha256"], bytes=entry["bytes"])
            _check_hash(checked_path(output, relative), entry, deadline)
            expected_copies.append(proof)
        else:
            path = checked_path(Path(roots[entry["root_alias"]]), entry["relative_path"])
            _check_hash(path, entry, deadline)
            expected_external.append(dict(source_id=entry["source_id"], path=str(path),
                                          sha256=entry["sha256"], bytes=entry["bytes"]))
        if entry["receipt"] is not None:
            ref = entry["receipt"]
            path = checked_path(Path(roots[ref["root_alias"]]), ref["relative_path"])
            original = _read(path, deadline)
            relative = POLICY_DIR + "/receipts/" + ref["sha256"] + ".json"
            archived = _read(checked_path(output, relative), deadline)
            need(original == archived and _descriptor("", archived)["sha256"] == ref["sha256"],
                 "original receipt differs from immutable archive")
            _check_receipt(entry, roots, archived, deadline)
            expected_receipts.append(dict(source_id=entry["source_id"], original_path=str(path),
                                          **_descriptor(relative, archived)))
    for name, expected in (("copies", expected_copies), ("external_sources", expected_external),
                           ("receipts", expected_receipts)):
        need(canonical(seal[name]) == canonical(expected), "sealed " + name + " inventory differs")
    expected_execution = dict(case=POLICY_DIR + "/case.json", snapshot=POLICY_DIR + "/inputs/snapshot.json",
                              catalog=POLICY_DIR + "/projection.json")
    need(seal["execution"] == expected_execution, "execution controls differ")
    case = decode(Case, controls["case"])
    store = load_snapshot(checked_path(output, expected_execution["snapshot"]), case,
                          checked_path(output, expected_execution["catalog"]))
    if check_engine:
        inputs = parse_json(_read(output / "engine/inputs.json", deadline))
        run = parse_json(_read(output / "engine/run.json", deadline))
        need(canonical(inputs["case"]) == canonical(encode(case)) and
             canonical(inputs["snapshot"]) == canonical(encode(store.snapshot)) and
             canonical(inputs["catalog_policy"]) == canonical(decision["projection"]) and inputs["scorer"] is None and
             inputs["snapshot_base"] == str((output / POLICY_DIR / "inputs").resolve()) and
             run["backend_id"] == "offline-extractive-v1", "engine consumed controls outside sealed policy")
    return dict(method=METHOD, status="artifact_policy_consistency_verified", policy_id=controls["policy"]["policy_id"],
                use_id=seal["use_id"], frame_sha256=seal["frame_sha256"], checked_inputs=len(decision["binding"]["inventory"]),
                scientific_validation="not_established")
