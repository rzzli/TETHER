"""Copy a frozen P09 allowlist and exact local inputs into a fresh C: temp root.

Local preparation only. Does not install packages or run reconstruction, audit,
models or downloads. Every original/receipt remains read-only and hash checked.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from asof.journal import RunJournal
from asof.serde import canonical, parse_json
from asof.study.stable_read import checked_path, stable_files


def need(value, message):
    if not value:
        raise ValueError(message)


def copy_exact(source, destination, expected_sha, expected_bytes):
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest, total = hashlib.sha256(), 0
    with source.open("rb") as incoming, destination.open("xb") as outgoing:
        while block := incoming.read(8 * 1024**2):
            total += len(block)
            need(total <= expected_bytes, "Original exceeds frozen length")
            digest.update(block)
            outgoing.write(block)
    need(total == expected_bytes and digest.hexdigest() == expected_sha, "Original/copy anchor mismatch")
    reread = hashlib.sha256()
    with destination.open("rb") as stream:
        while block := stream.read(8 * 1024**2):
            reread.update(block)
    need(reread.hexdigest() == expected_sha, "Relocated readback differs")


def prepare(bundle, protocol_sha, original_root, output):
    # Only this explicit local qualification destination is writable by this tool.
    temporary_parent = Path(r"C:\Users\zzric\AppData\Local\Temp").resolve()
    output = output.resolve()
    need(output.parent == temporary_parent and output.name.startswith("asof-p09-"),
         "Relocation must reserve a new direct asof-p09-* child of the approved C: temporary root")
    need(not output.exists(), "Relocation destination already exists")
    raw = (bundle / "protocol.json").read_bytes()
    need(hashlib.sha256(raw).hexdigest() == protocol_sha, "External READY protocol hash differs")
    protocol = parse_json(raw)
    need(protocol.get("status") == "READY" and protocol.get("actual_reconstruction_authorized") is True,
         "Relocation requires the separately frozen authorized READY")
    policy_desc = protocol["source_policy"]
    policy_raw = checked_path(bundle, policy_desc["path"]).read_bytes()
    need(hashlib.sha256(policy_raw).hexdigest() == policy_desc["sha256"], "Source policy anchor differs")
    policy = parse_json(policy_raw)
    inventory = [dict(path=i["relative_path"], sha256=i["sha256"], bytes=i["bytes"]) for i in policy["inventory"]]
    inventory += [dict(path=i["receipt"]["relative_path"], sha256=i["receipt"]["sha256"], bytes=i["receipt"]["bytes"])
                  for i in policy["inventory"]]
    need(len(inventory) == 274 and len({i["path"] for i in inventory}) == 274, "Complete distinct 137-original/receipt inventory required")
    files = protocol["files"]
    sources = [checked_path(bundle, name) for name in files] + [checked_path(original_root, i["path"]) for i in inventory]
    journal = RunJournal(output, kind="build")
    started = time.monotonic()
    try:
        journal.append("build_stage", stage="frozen_local_relocation", protocol_sha256=protocol_sha)
        deadline = started + 1200
        with stable_files(sources, deadline=deadline):
            for logical, descriptor in files.items():
                need(logical == descriptor["path"], "Bundle logical identity differs")
                copy_exact(checked_path(bundle, logical), output / "bundle" / logical,
                           descriptor["sha256"], descriptor["bytes"])
            (output / "bundle/protocol.json").write_bytes(raw)
            for index, descriptor in enumerate(inventory):
                need(time.monotonic() < deadline, "Relocation time limit exceeded")
                copy_exact(checked_path(original_root, descriptor["path"]), output / "originals" / descriptor["path"],
                           descriptor["sha256"], descriptor["bytes"])
                if (index + 1) % 20 == 0:
                    journal.append("build_progress", stage="frozen_local_relocation", verified_inputs=index + 1)
        report = dict(schema_version=1, method="p09.local_relocation.v1", status="COPIED_AND_HASH_VERIFIED",
            protocol_sha256=protocol_sha, bundle_members=len(files) + 1, original_files=137, receipt_files=137,
            original_bytes=sum(i["bytes"] for i in policy["inventory"]),
            receipt_bytes=sum(i["receipt"]["bytes"] for i in policy["inventory"]),
            copy_and_readback_seconds=time.monotonic() - started,
            reconstruction_executed=False, new_downloads=0, model_calls=0, provider_spending_usd=0)
        (output / "relocation.json").write_bytes(canonical(report) + b"\n")
        journal.append("build_completed", stage="frozen_local_relocation", report_sha256=hashlib.sha256(canonical(report) + b"\n").hexdigest())
        print(canonical(report).decode())
        return report
    except BaseException as error:
        journal.fail(error, "frozen_local_relocation")
        raise
    finally:
        journal.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--originals-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.bundle_root.resolve(), args.protocol_sha256, args.originals_root.resolve(), args.output)


if __name__ == "__main__":
    main()
