"""Root acceptance for exact schema and independent literal preparation only."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXPECTED = {
    "ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json": "b71cd8f49ccc8d4dc56b31915a3ed20465f58b08bb35b54df63a73a49e655b7a",
    "ROLE-AWARE-PRODUCER-FORMAT-FREEZE-v2.json": "6840693d791d2a996dd82e195bf91f35ed10b163d10d3d57f38d607628d161da",
    "ROLE-AWARE-PRODUCER-FORMAT-INDEPENDENT-REVIEW-v2.json": "7828e2151035316f73aa89ec58891a5fc97104b1370d79e5b3e2cc29c6fe5466",
    "ROLE-AWARE-PRODUCER-FORMAT-EVIDENCE-INDEX-v2.json": "4560bf6b826096a5d1cd410e4c6da935c2e1862fba8c62c3f9f6389481ac74c1",
    "ROLE-AWARE-PRODUCER-FORMAT-ROOT-CLARIFICATION-CHOICE-v2.json": "97c2c67232660c6c5e9a457a62aec07afef2a1754e6bc28ba87a67b51d2dd9d4",
}


def pin(path):
    assert path.resolve().parent == HERE
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def read(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def main():
    inputs = {}
    for name, expected in EXPECTED.items():
        inputs[name] = pin(HERE / name)
        assert inputs[name]["sha256"] == expected, name
    index = read("ROLE-AWARE-PRODUCER-FORMAT-EVIDENCE-INDEX-v2.json")
    for record in index["pins"]:
        path = Path(record["path"])
        if not path.is_absolute():
            path = ROOT / path
        observed = pin(path)
        assert (observed["bytes"], observed["sha256"]) == (record["bytes"], record["sha256"])
    peer = read("ROLE-AWARE-PRODUCER-FORMAT-INDEPENDENT-REVIEW-v2.json")
    assert peer["status"].startswith("CLEAR") and peer["material_blockers"] == []
    schema = read("ROLE-AWARE-PRODUCER-FORMAT-CONTRACT-v2.json")
    for key, width in (("header", 4096), ("call_record", 256), ("file_record", 256), ("module_record", 64), ("diagnostic_record", 1024), ("section_descriptor", 64)):
        table = schema[key]
        assert table["bytes"] == width
        offset = 0
        for field in table["fields"]:
            assert field["offset"] == offset, (key, field["name"])
            offset += field["bytes"]
        # Header fields explicitly include the descriptor table/reserved ranges.
        assert offset == width, key
    assert [api["id"] for api in schema["apis"]] == list(range(1, 15))
    assert [api["id"] for api in schema["apis"] if api["complete_ledger_allowed"]] == list(range(1, 8))
    assert len(schema["sections"]) == 8 and set(schema["question_answers"]) == {"Q" + str(i) for i in range(1, 11)}
    assert schema["fixture_plan"]["maximum_histories"] == 40
    assert schema["qualification"]["encoder_implemented"] is False and schema["qualification"]["producer_implemented"] is False
    inputs[Path(__file__).name] = pin(Path(__file__))
    result = {
        "schema_version": 1, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ACCEPTED_EXACT_FORMAT_SCHEMA_FOR_INDEPENDENT_LITERAL_PREPARATION_ONLY",
        "inputs": inputs, "verified_index_pins": len(index["pins"]),
        "closed": ["Ten required schema groups are explicit; five pre-golden clarification groups closed without layout-width changes.",
                   "Primary live slots precede all packing; encoded records/decoded data carry no owner or runtime authority.",
                   "Actual producer/legacy identity and byte issuance remain separate from pure codec tests."],
        "literal_preparation_authorized": True,
        "literal_scope": "Independent synthetic fixed byte literals, schema semantic expectations, malformed-byte expansions and immutable/cancellation controls. At most40 semantic base histories; bind and honestly count all byte negatives, field anchors, calls and deferred producer controls before encoder implementation. Full-cap generated layouts are shape tests, not real histories or resource qualification.",
        "source_implementation_authorized": False, "producer_integration_qualified": False,
        "original_payload_operations": 0, "native_or_physical_operations": 0,
        "full_roster_admitted": False, "new84_runtime": False, "measured_resource_fit": False,
        "scientific_validation": False, "application_changed": False, "provider_spending": 0,
        "next": "Freeze independently reviewed exact literals/test source and retain data-only checks, then authorize one concrete encoder-plus-producer implementation slice. Do not add another abstract calculator or treat codec-only results as live provenance.",
    }
    output = HERE / "ROLE-AWARE-PRODUCER-FORMAT-SCHEMA-ACCEPTANCE-v2.json"
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "sha256": pin(output)["sha256"], "verified_index_pins": len(index["pins"])}))


if __name__ == "__main__":
    main()
