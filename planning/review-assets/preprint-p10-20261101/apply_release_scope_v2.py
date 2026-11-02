"""Clarify the supplement opening; retain candidate 1 and complete inverse proof."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    proof_path = HERE / "SOURCE-DELTA-v1.json"
    prior = proof_path.read_bytes()
    record = json.loads(prior)
    old = "The public release and author declarations are not yet qualified."
    new = "Public deposit and owner declarations remain pending. The separately qualified local artifact is described in S8."
    source = ROOT / "paper/supplement.md"
    raw = source.read_bytes()
    assert sha(raw) == record["sources"]["supplement.md"]["after_sha256"]
    assert raw.count(old.encode()) == 1 and new.encode() not in raw
    changed = raw.replace(old.encode(), new.encode(), 1)
    record["sources"]["supplement.md"]["edits"].append({"old": old, "new": new})
    record["sources"]["supplement.md"]["after_sha256"] = sha(changed)
    for name, item in record["sources"].items():
        inverse = changed if name == "supplement.md" else (ROOT / "paper" / name).read_bytes()
        for edit in reversed(item["edits"]):
            assert inverse.count(edit["new"].encode()) == 1
            inverse = inverse.replace(edit["new"].encode(), edit["old"].encode(), 1)
        assert sha(inverse) == item["before_sha256"]
    retained = ROOT / "data/derived/preprint-p10-20261101/candidate1"
    retained.mkdir(parents=True, exist_ok=False)
    for name in ("asof-source-reporting-preprint-v2.pdf", "PDF-BUILD-v2.json", "supplement.md"):
        shutil.copyfile(ROOT / "paper" / name, retained / name)
    source.write_bytes(changed)
    record["edited_paragraphs"] = 4
    record["prior_delta_sha256"] = sha(prior)
    record["correction"] = "Clarify supplement opening status after visual review; local qualification and public deposit are separate."
    with (HERE / "SOURCE-DELTA-v2.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"status": record["status"], "supplement_sha256": sha(changed), "edited_paragraphs": 4}))


if __name__ == "__main__":
    main()
