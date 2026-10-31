"""Source preparation acceptance only; no runtime pack or native invocation."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
PINS = {
    "UNICODE-WIRE-DESIGN-CONTRACT-v2.json": "ddf9fd360d72def0b91bd99b047422bf8ee623c0f8d6e0ba73535e04a7af1abc",
    "UNICODE-WIRE-FRAMING-CONTRACT-v1.json": "4c4645f53c878e03cf1f0eaec575b3dcf1dcc006375aadc0080819393e4c3d24",
    "UNICODE-WIRE-FRAMING-CONTRACT-FREEZE-v1.json": "83505601fa786f4df1844dd0f45d9ffe10944a1c04e32b6c5326fb7099efbba7",
    "UNICODE-WIRE-FRAMING-FIXTURES-v1.json": "f81f351e61a5e4bd5c9c9d8475b9d6ad51239b94320156409fff25fde40894eb",
    "UNICODE-WIRE-FRAMING-FREEZE-v1.json": "5a7bd2876fc072a8984646200039751da3af9461356b0d8f34c26ed54419b075",
    "UNICODE-WIRE-FRAMING-STRUCTURAL-PROOF-v1.json": "b3451a50715cf67b1289fe86675c61d36e514a9f9c7450242da71d9e1193ba71",
    "UNICODE-WIRE-FRAMING-INDEPENDENT-PEER-v1.json": "31f64026e4c61b5ef16dc8f7b0885f43b682c0bc236d61536c632afe850176ca",
}


def main():
    blobs, pins = {}, {}
    for name, expected in PINS.items():
        data = (HERE / name).read_bytes()
        actual = hashlib.sha256(data).hexdigest()
        if actual != expected:
            raise ValueError("Framing preparation pin mismatch: " + name)
        blobs[name] = data
        pins[name] = {"bytes": len(data), "sha256": actual}
    author = json.loads(blobs["UNICODE-WIRE-FRAMING-STRUCTURAL-PROOF-v1.json"])
    peer = json.loads(blobs["UNICODE-WIRE-FRAMING-INDEPENDENT-PEER-v1.json"])
    assert author["status"] == "passed" and author["methods"] == 7
    assert author["failures"] == author["errors"] == []
    assert peer["status"] == "CLEAR_FRAMING_DESIGN_AND_LITERAL_FIXTURES_ONLY"
    assert peer["material_findings"] == [] and peer["inputs_unchanged"] is True
    assert len(peer["checks"]) == 7 and all(row["status"] == "passed" for row in peer["checks"])
    assert peer["profile_qualified"] is False
    assert peer["effective_wire_semantics_sha256"] == "75605c03fb5b9bac659538035d8205b34df2ae1781b997a3181a1564676aa6c4"
    report = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_UNICODE_FRAMING_PREPARATION_ONLY",
        "inputs": pins, "author_methods": 7, "peer_groups": 7,
        "literal_fragments": 25, "literal_rows": 22, "negative_partial_histories": 14,
        "effective_wire_semantics_sha256": peer["effective_wire_semantics_sha256"],
        "scope": "Exact source schemas, enums, literal fragment framing, sizing envelopes and partial-history expectations. These are preparation; no complete runtime pack or behavioral native trace is validated.",
        "runtime_or_native_authority": False, "profile_qualified": False,
        "old_negative_and_timeout_unchanged": True,
        "next_scope": "A separate root implementation decision may authorize bounded source/pure in-memory codecs; no file preparation, bridge, parent, SDK or runtime is authorized by this acceptance.",
    }
    output = HERE / "UNICODE-WIRE-FRAMING-SCOPED-ACCEPTANCE-v1.json"
    with output.open("xb") as stream:
        stream.write((json.dumps(report, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"status": report["status"], "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}))


if __name__ == "__main__":
    main()
