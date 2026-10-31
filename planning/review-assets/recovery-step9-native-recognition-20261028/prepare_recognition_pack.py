"""Build own finite diagnostic input only: no download/target/model execution.

The original 167 documents keep their exact bytes. Eighteen new serialized
abstention fixtures are explicitly a new group, not recovered historical wire.
"""
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import sys
import time

from asof.serde import canonical
from asof.study import interpretation_grammar  # preload accepted installed module

ROOT = Path(__file__).resolve().parents[3]
PHASE = Path(__file__).resolve().parent
MANIFEST = ROOT / "data/cache/r09-generation-corpus-extension-v1-20261028/FUTURE-NATIVE-CORPUS-MANIFEST.json"
MANIFEST_SHA = "43aa4b18d3d9c7393198d0eaa93095999d1ef54f0d2757ffe6265c7d95a26e4a"
PROPOSAL_SHA = "1fca71287d74592581743d5aa3869612dde01afb5e5cb52e350be3b64a7eebca"
PREP = ROOT / "data/cache/r09-generation-preparation-20261028T052637Z"


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def safe(path):
    path = Path(path).absolute()
    require(path.is_relative_to(ROOT) and path.resolve().is_relative_to(ROOT.resolve()), "Path outside project")
    for parent in (path, *path.parents):
        try:
            status = parent.lstat()
        except FileNotFoundError:
            continue
        require(not parent.is_symlink() and not getattr(status, "st_file_attributes", 0) & 0x400,
                "Reparse path rejected")
    return path


def write_new(path, raw):
    with safe(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def main():
    require(os.name == "nt" and sys.flags.isolated and sys.dont_write_bytecode, "Windows -I -B required")
    require(interpretation_grammar.__file__.startswith(str(ROOT / "data/cache/recovery-step9-generation-wheel-20261028/environment")),
            "Accepted installed package required")
    output = safe(ROOT / "data/cache" / ("r09-native-recognition-pack-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")))
    output.mkdir()
    started = time.monotonic()
    inputs, grammars, cases, prefixes = {}, [], [], []
    report = dict(schema_version=1, status="failed", output=str(output), execution_authorized=False,
                  native_target_calls=0, gguf_reads=0, model_calls=0, provider_spend_usd=0)

    def read(path, expected=None):
        require(time.monotonic() - started < 60, "Input preparation deadline")
        path = safe(path)
        require(path.stat().st_size <= 2 * 1024 * 1024, "Unexpected large input")
        raw = path.read_bytes()
        digest = sha(raw)
        require(expected is None or digest == expected, "Input hash differs: " + str(path))
        item = dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=digest)
        require(item["path"] not in inputs or inputs[item["path"]] == item, "Input changed")
        inputs[item["path"]] = item
        return raw

    def grammar(raw):
        digest = sha(raw)
        require(0 < len(raw) <= 65536 and b"\0" not in raw, "Grammar limit")
        raw.decode("utf-8")
        for i, item in enumerate(grammars):
            if item["sha256"] == digest:
                require(item["raw"] == raw, "Grammar identity collision")
                return i
        grammars.append(dict(id=f"grammar/{len(grammars)}", sha256=digest, raw=raw))
        return len(grammars) - 1

    def add_case(case_id, group, index, kind, raw, provenance):
        require(len(raw) <= 65536 and not any(item["id"] == case_id for item in cases), "Case size/duplicate")
        case_id.encode("ascii")
        require(0 < len(case_id) <= 256 and all(32 <= ord(c) <= 126 for c in case_id), "Case ID")
        cases.append(dict(id=case_id, source_group=group, grammar_index=index, expected_kind=kind,
                          raw=raw, bytes=len(raw), sha256=sha(raw), provenance=provenance))

    try:
        proposal = json.loads(read(PHASE / "NATIVE-CORPUS-PROPOSAL.json", PROPOSAL_SHA))
        for item in proposal["artifact_refs"]:
            read(ROOT / item["path"], item["sha256"])
        manifest = json.loads(read(MANIFEST, MANIFEST_SHA))
        require(len(manifest["cases"]) == 167, "Frozen primary count differs")
        variants = {}
        for variant, files in manifest["variants"].items():
            binding = files["grammar.gbnf"]
            variants[variant] = grammar(read(ROOT / binding["path"], binding["sha256"]))
        legacy = json.loads(read(ROOT / "data/cache/r09-native-grammar-corpus-20261028/cases.json",
                                 "01286d35689c7005ea67fa817c4b4098cecd05c4233c3949e7ec744bc5f5d97a"))
        legacy = {item["id"]: item for item in legacy}
        for number, item in enumerate(manifest["cases"]):
            if item["document_path"] is None:
                raw = legacy[item["original_corpus_case_id"]]["document_json"].encode("utf-8")
            else:
                raw = read(ROOT / item["document_path"], item["document_sha256"])
            require(len(raw) == item["document_bytes"] and sha(raw) == item["document_sha256"], "Primary bytes differ")
            require(type(item["observed_pure_membership"]) is bool, "Missing prospective membership observation")
            add_case(f"primary/{number:03d}", 0, variants[item["variant"]], int(item["observed_pure_membership"]), raw, item)
        require(sum(item["expected_kind"] for item in cases) == 44, "Primary 44/123 disposition differs")

        # Receipt-verifiable wrappers contain parsed fixture objects, not raw answer wire.
        receipt = json.loads(read(PREP / "receipt.json", "1b68e94d6c03723b7008c42f51e2c54e8597fcf28be47c81b3a992e29be43d4f"))
        receipt_outputs = {Path(key).as_posix(): value for key, value in receipt["outputs"].items()}
        require(len(receipt_outputs) == len(receipt["outputs"]), "Ambiguous normalized receipt paths")
        prepared = json.loads(read(PREP / "report.json", "a2af762049dd5fc4b62f71d1b1f88c34aca4280140515b1e5e0955b894d174a7"))
        require(len(prepared["records"]) == 18, "Preparation count differs")
        for i, item in enumerate(prepared["records"]):
            path = safe(item["preparation_file"])
            require(path.is_relative_to(PREP), "Unexpected preparation path")
            texts = []
            for original in (path, path.with_name("response-fixture.json")):
                pin = receipt_outputs[original.relative_to(PREP).as_posix()]
                raw = read(original, pin["sha256"])
                require(len(raw) == pin["bytes"], "Preparation size differs")
                texts.append(json.loads(raw))
            preparation, fixture = texts
            require(sha(canonical(fixture)) == item["response_fixture_sha256"], "Logical fixture differs")
            require(preparation["request_sha256"] == item["request_sha256"]
                    and preparation["payload_sha256"] == item["payload_sha256"], "Preparation record binding differs")
            for key in ("request_sha256", "payload_sha256", "generation_contract_sha256",
                        "quote_catalog_sha256", "acceptance_schema_sha256"):
                require(fixture[key] == preparation[key], "Fixture/preparation binding differs: " + key)
            require(fixture["response"]["answer_status"] == "abstained" and fixture["features"] == {}
                    and fixture["clinical_probability"] is None, "Unexpected scientific fixture")
            bundle = preparation["generation_grammar"]
            raw_grammar = bundle["grammar"].encode("utf-8")
            require(sha(raw_grammar) == bundle["grammar_sha256"] == item["grammar_sha256"]
                    and len(raw_grammar) == bundle["grammar_bytes"] == item["grammar_bytes"], "Preparation grammar differs")
            index = grammar(raw_grammar)
            raw = canonical(fixture["response"])
            add_case(f"new-abstention/{i:02d}", 1, index, 1, raw,
                     dict(group="new_serialization_of_retained_authored_abstention", original_wrapper=path.with_name("response-fixture.json").relative_to(ROOT).as_posix(),
                          serialization="asof.serde.canonical compact sorted UTF8, no appended newline", historical_raw_wire=False,
                          case=item["case"], arm=item["arm"], stage=item["stage"], scientific_validation="not_established"))
        for guard in proposal["proposed_byte_guards"]:
            raw = bytes.fromhex(guard["hex"])
            require(sha(raw) == guard["sha256"] and len(raw) == guard["bytes"], "Guard differs")
            add_case(guard["id"], 2, 0, 2 if "utf8" in guard["expected"] else 3, raw, guard)
        require(len(cases) == 189 and len(grammars) <= 20, "Finite pack counts differ")

        # Execute only a pinned, trusted own-source pure oracle. Its source-path
        # insertion is restored, and the accepted grammar module was preloaded.
        oracle_path = ROOT / "planning/review-assets/recovery-step9-generation-contract-20261028/finite_gbnf_oracle.py"
        frozen = json.loads(read(ROOT / "data/cache/r09-generation-corpus-extension-v1-20261028/FROZEN-INPUTS.json",
                                "1b80e365e42b28fe237c22fc35e215d1a0410729203a77255fc628309a9da414"))
        expected = frozen["source_pins"][oracle_path.relative_to(ROOT).as_posix()]
        read(oracle_path, expected)
        spec = importlib.util.spec_from_file_location("r09_frozen_pure_oracle", oracle_path)
        oracle = importlib.util.module_from_spec(spec)
        previous = sys.path[:]
        try:
            spec.loader.exec_module(oracle)
        finally:
            sys.path[:] = previous
        rules = [oracle.parse(item["raw"].decode("utf-8")) for item in grammars]
        for item in cases:
            if item["source_group"] != 2:
                observed = oracle.accepts(rules[item["grammar_index"]], "root", item["raw"].decode("utf-8"))
                require(observed == bool(item["expected_kind"]), "Prospective pure membership differs: " + item["id"])

        positions = {item["provenance"]["id"]: i for i, item in enumerate(cases) if item["source_group"] == 0}
        for proposal_prefix in proposal["proposed_prefixes"]:
            base_index = positions[proposal_prefix["base_id"]]
            base = cases[base_index]
            require(base["expected_kind"] == 1, "Prefix base is not a pure member")
            identity = proposal_prefix["id"]
            if identity.endswith("natural_partial_bmp") or identity.endswith("natural_partial_astral"):
                kind = 1 if identity.endswith("bmp") else 2
                cut, digest = 0, "0" * 64
            else:
                kind = 0
                if identity == "prefix/empty":
                    cut = 0
                elif identity == "prefix/final_close_missing":
                    require(base["raw"].endswith(b"}"), "Closing byte changed")
                    cut = len(base["raw"]) - 1
                else:
                    match = re.search(rb"\\u[Dd][89AaBb][0-9A-Fa-f]{2}\\u[Dd][CcDdEeFf][0-9A-Fa-f]{2}", base["raw"])
                    require(match is not None, "Specified surrogate pair missing")
                    cut = match.start() + (1 if identity == "prefix/escape_backslash" else 6)
                raw = base["raw"][:cut]
                text = raw.decode("utf-8")
                require(b"\0" not in raw and not oracle.accepts(rules[base["grammar_index"]], "root", text), "Byte prefix not incomplete")
                digest = sha(raw)
            prefixes.append(dict(id=identity, base_case_index=base_index, kind=kind, cut=cut, sha256=digest,
                                 provenance=proposal_prefix, natural_boundary_coverage="unknown" if kind else "not_applicable"))

        packed = bytearray(b"R09NC01\0")
        def u32(value):
            require(type(value) is int and 0 <= value < 2**32, "u32 range")
            packed.extend(struct.pack("<I", value))
        def blob(value):
            u32(len(value)); packed.extend(value)
        for value in (1, len(grammars), len(cases), len(prefixes)):
            u32(value)
        for item in grammars:
            blob(item["id"].encode("ascii")); packed.extend(bytes.fromhex(item["sha256"])); blob(item["raw"])
        for item in cases:
            blob(item["id"].encode("ascii"))
            for key in ("source_group", "grammar_index", "expected_kind"):
                u32(item[key])
            packed.extend(bytes.fromhex(item["sha256"])); blob(item["raw"])
        for item in prefixes:
            blob(item["id"].encode("ascii"))
            for key in ("base_case_index", "kind", "cut"):
                u32(item[key])
            packed.extend(bytes.fromhex(item["sha256"]))
        require(len(packed) <= 20 * 1024**2, "Pack cap")
        write_new(output / "recognition.pack", packed)
        clean = lambda item: {key: value for key, value in item.items() if key != "raw"}
        report.update(status="prepared_pure_membership_checked_no_native", primary_frozen_documents=167,
            newly_serialized_authored_abstentions=18, independent_byte_guards=4, cases=[clean(x) for x in cases],
            grammars=[clean(x) for x in grammars], prefixes=prefixes, inputs=list(inputs.values()),
            pack=dict(path=str(output / "recognition.pack"), bytes=len(packed), sha256=sha(packed)),
            elapsed_seconds=time.monotonic() - started,
            limits="No native authorization; pure oracle is own-source comparator, not native conformance or scientific validation")
    except BaseException as error:
        report["failure"] = dict(error_class=type(error).__name__, error=str(error))
        raise
    finally:
        write_new(output / "preparation-report.json", canonical(report) + b"\n")
        print(json.dumps({key: report[key] for key in ("status", "output")}))


if __name__ == "__main__":
    main()
