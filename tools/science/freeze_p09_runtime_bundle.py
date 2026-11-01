"""Root freeze of the reviewed P09 draft into a separate runtime-only bundle."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from asof.serde import canonical, parse_json
from asof.study.stable_read import checked_path

DRAFT_SHA = "f451c523387eec94155b0f24b62762adffc380a73cf83401f099530efce43d1c"


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def freeze(draft, output, review, review_sha, record, draft_sha=DRAFT_SHA):
    output = output.resolve()
    need(output.is_relative_to((ROOT / "data/cache").resolve()) and not output.exists(), "Fresh ignored runtime bundle required")
    need(not record.exists(), "Freeze record already exists")
    raw = (draft / "protocol.json").read_bytes()
    need(sha(raw) == draft_sha, "Reviewed draft authority differs")
    protocol = parse_json(raw)
    review_raw = review.read_bytes()
    need(sha(review_raw) == review_sha, "Independent bundle review anchor differs")
    checked = parse_json(review_raw)
    need(checked["status"] == "PASS_DRAFT_METADATA_REVIEW" and checked["protocol_sha256"] == draft_sha and
         not checked["unresolved_findings"] and not checked["privacy_findings"], "A passing independent allowlist review is required")
    need(protocol["status"] == "DRAFT_ROOT_AUTHORIZATION_PENDING" and protocol["actual_reconstruction_authorized"] is False and
         protocol["dataset_payloads"]["hgnc_included"] is True and len(protocol["files"]) == 311,
         "Unexpected draft or mandatory HGNC exception missing")
    output.mkdir(parents=True)
    # Preparation journal and report are not protocol members. Never copy the
    # whole draft tree; the runtime auditor rejects undeclared files.
    for logical, descriptor in protocol["files"].items():
        need(logical == descriptor["path"], "Logical member identity differs")
        payload = checked_path(draft, logical).read_bytes()
        need(len(payload) == descriptor["bytes"] and sha(payload) == descriptor["sha256"], "Draft member changed: " + logical)
        target = output / logical
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(payload)
        need(target.read_bytes() == payload, "Runtime member readback differs")
    frozen = datetime.now(timezone.utc).isoformat()
    protocol.update(status="READY", actual_reconstruction_authorized=True,
                    frozen_at_utc=frozen, independent_bundle_review_sha256=review_sha)
    final_raw = canonical(protocol) + b"\n"
    with (output / "protocol.json").open("xb") as stream:
        stream.write(final_raw)
    need(sha((output / "protocol.json").read_bytes()) == sha(final_raw), "Runtime protocol readback differs")
    observed = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
    need(observed == set(protocol["files"]) | {"protocol.json"}, "Runtime whole-file closure differs")
    ready = dict(schema_version=1, status="READY_FOR_INSTALLED_LOCAL_RECONSTRUCTION", frozen_at_utc=frozen,
        runtime_bundle=output.relative_to(ROOT).as_posix(), protocol_sha256=sha(final_raw),
        draft_protocol_sha256=draft_sha, independent_bundle_review_sha256=review_sha,
        code_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        core_files=protocol["core_files"], replay_files=protocol["replay_files"], environment=protocol["environment"],
        limits=protocol["limits"], allowlisted_members=len(protocol["files"]),
        required_originals=137, required_receipts=137, planned_outputs=38, planned_decisions=90,
        actual_execution_recorded=False, original_experiment_repeated=False, publication_authorized=False,
        scientific_validation="not_established", owner_declarations="deferred", model_calls=0, new_downloads=0,
        provider_spending_usd=0, freezer_sha256=sha(Path(__file__).read_bytes()))
    record.parent.mkdir(parents=True, exist_ok=True)
    with record.open("xb") as stream:
        stream.write(canonical(ready) + b"\n")
    print(canonical(dict(status=ready["status"], protocol_sha256=ready["protocol_sha256"], runtime_bundle=ready["runtime_bundle"])).decode())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("draft", "output", "review", "record"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--review-sha256", required=True)
    parser.add_argument("--draft-sha256", default=DRAFT_SHA)
    args = parser.parse_args()
    freeze(args.draft.resolve(), args.output, args.review, args.review_sha256, args.record, args.draft_sha256)


if __name__ == "__main__":
    main()
