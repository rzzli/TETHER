"""Author fixture-only synthetic pieces/declarations, not a validator or tokenizer."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent / "recovery-step9-unicode-control-20261029/UNICODE-CONTROL-CORPUS-v1.json"
PLAN = HERE / "UNICODE-OBSERVATIONS-TRACE-AUTHORING-PLAN-v2.json"
TARGET = HERE / "UNICODE-OBSERVATIONS-SYNTHETIC-CONTEXT-v1.json"
FREEZE = HERE / "UNICODE-OBSERVATIONS-SYNTHETIC-CONTEXT-FREEZE-v1.json"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def pieces(raw, mixed):
    join = next((i-1 for i in range(1, len(raw)) if 0xc2 <= raw[i] <= 0xf4 and raw[i-1] < 0x80), None) if mixed else None
    result = [b""]; at = 0
    while at < len(raw):
        size = 2 if at == join else 1
        result.append(raw[at:at+size]); at += size
    return result


def pin(path):
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    assert not TARGET.exists() and not FREEZE.exists()
    assert pin(CORPUS)["sha256"] == "13e2c2f2900802729c0d39fa9b7851c56ab3db6afdc45c4b15c2f7f80bd6523c"
    source = json.loads(CORPUS.read_bytes())
    unique = set()
    for row in source["cases"]:
        if row["expected"]["native_byte_eligible"]:
            for mixed in (False, True): unique.update(pieces(bytes.fromhex(row["raw_hex"]), mixed))
    table = [dict(id=index, bytes=len(raw), piece_hex=raw.hex()) for index, raw in enumerate(sorted(unique))]
    assert len(table) < 1022 and table[0] == dict(id=0, bytes=0, piece_hex="")
    def declared(index):
        return dict(path=rf"D:\synthetic\unicode\payload\part-{index}.gguf", bytes=17,
                    sha256=hashlib.sha256(f"fictional shard {index}".encode("ascii")).hexdigest())
    context = dict(schema_version=1, status="FICTIONAL_FIXED_VOCABULARY_AND_RUNTIME_DECLARATIONS_ONLY",
        expected_child_pid=4242, expected_self=r"D:\synthetic\unicode\recognizer.exe",
        expected_runtime=r"D:\synthetic\unicode\runtime", ordered_shard_descriptors=[declared(i) for i in (1, 2, 3)],
        expected_newpack_sha256="d2537df43e7e6e8113c4e08f0536c2e3a698bd274963ab71a4efced4fa32c8ab",
        vocabulary_size=1024, EOG_ids=[1022, 1023], ordinary_piece_table=table,
        token_piece_rule="Each ordinary ID maps to exactly one global byte string across allcases/prefixes. Tokenizer pieces are authored deterministic synthetic splits, not actual observed IDs.",
        expected_stage_ids=["mechanism_asof0", "genetics_asof0", "mechanism_vb_chief0", "genetics_vb_chief0"],
        plan_sha256=pin(PLAN)["sha256"], corpus_sha256=pin(CORPUS)["sha256"],
        profile_qualified=False, originals_authenticated=False, runtime_authorized=False,
        source_or_payload_path_operations=0, native_calls=0)
    raw = canonical(context)+b"\n"
    with TARGET.open("xb") as out: out.write(raw)
    freeze = dict(schema_version=1, status="fixture_piece_table_frozen_before_complete_trace_authoring",
        context=pin(TARGET), author=pin(Path(__file__).resolve()), plan=pin(PLAN), corpus=pin(CORPUS),
        ordinary_piece_ids=len(table), vocabulary_size=1024, EOG_ids=[1022, 1023],
        source_bodies_changed=False, observation_validator_implemented=False, actual_tokenizer_observations=0,
        runtime_pack_file_created=False, SDK_native_payload_operations=0)
    with FREEZE.open("xb") as out: out.write(canonical(freeze)+b"\n")
    print(json.dumps(dict(context_sha256=pin(TARGET)["sha256"], freeze_sha256=pin(FREEZE)["sha256"], ordinary_piece_ids=len(table))))


if __name__ == "__main__": main()
