"""Finite source-component acceptance; not an OS/resource verifier."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "CAPTURED-JOB-BYTES-CONTRACT-v2.json": "3ed4e7cdffc16875864ba895566f36f24c938f981fd609ce32a40876999c36ca",
    "CAPTURED-JOB-BYTES-FIXTURES-v1.json": "e7a7668c190995b518983b3de3b573aca0ba9f6208ec531e0cef99b7b5b0e6ec",
    "CAPTURED-JOB-BYTES-FIXTURE-FREEZE-v1.json": "f95018fb8a0a23adf700f19cf85712133b29f47a279c46f6a97f88958652b22d",
    "captured_job_bytes_v1.py": "fd655c8bcec6091565492dbaafdd59f0e5d5ce87520d83edc8b94caaa9a7a8bd",
    "check_captured_job_bytes_v1.py": "60b37eadb39140b0f08e0af87da23c9052284fd072f901947f0e4e100c408c4a",
    "CAPTURED-JOB-BYTES-PURE-PROOF-v1.json": "5cd17eb925a0128cae5d0de0024d63d7371519570f2a08a370270b7a3c6d9e54",
    "CAPTURED-JOB-BYTES-INDEPENDENT-PEER-v1.json": "39661d54637d29716cd322d06f2b2edb671bd98da47b50334a745d88ef8b7d09",
    "CAPTURED-JOB-BYTES-INDEPENDENT-PROOF-v1.json": "cda50dd118215386fc29a97e28b9a1680b91da2e89fb404b14f1ae241755662f",
}


def main():
    blobs, checked = {}, {}
    for name, expected in PINS.items():
        data = (HERE / name).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected:
            raise ValueError("Job-byte component pin mismatch: " + name)
        blobs[name] = data
        checked[name] = {"bytes": len(data), "sha256": digest}
    author = json.loads(blobs["CAPTURED-JOB-BYTES-PURE-PROOF-v1.json"])
    peer = json.loads(blobs["CAPTURED-JOB-BYTES-INDEPENDENT-PEER-v1.json"])
    independent = json.loads(blobs["CAPTURED-JOB-BYTES-INDEPENDENT-PROOF-v1.json"])
    assert author["status"] == "passed" and author["methods"] == 8
    assert type(author["failures"]) is int and type(author["errors"]) is int
    assert author["failures"] == author["errors"] == 0
    assert peer["status"] == "CLEAR_SOURCE_PURE_ONLY" and peer["methods"] == 7
    assert peer["material_findings"] == [] and peer["source_pins_unchanged"] is True
    assert peer["resource_qualified"] is False and peer["runtime_or_execution_authority"] is False
    assert independent["status"] == "passed" and independent["methods"] == 7
    assert independent["failures"] == independent["errors"] == []
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_PURE_JOB_BYTE_DECODER_PHASE_COMPONENT_ONLY",
        "inputs": checked, "author_methods": 8, "peer_methods": 7,
        "literal_captures": 16, "literal_phase_checks": 18,
        "author_mutation_vectors": 29, "independent_vectors": 49,
        "scope": "Captured Win64 48/136-byte decoding, source-view consistency and selected non-atomic phase tuples. Variable PID returned length, signed64/u32/u64 fields and ignored unused tail are tested. No original-source, PID ownership or OS-enforcement proof.",
        "resource_qualified": False, "atomic_snapshot": False,
        "runtime_or_execution_authority": False,
        "old_negative_and_timeout_unchanged": True,
        "remaining": ["Actual capture/provenance/journal/archive/source binding", "Memory-limit/peak/EOF/exit/reaping/cleanup and original-clock checks", "Real platform/entry/engine and future profile qualification"],
    }
    output = HERE / "CAPTURED-JOB-BYTES-SCOPED-ACCEPTANCE-v1.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(result, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": result["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
