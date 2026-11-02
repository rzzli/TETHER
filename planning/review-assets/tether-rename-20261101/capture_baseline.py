"""Retain pre-rename proof metadata; never parse protected or provider originals."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    commit = subprocess.check_output(["git", "rev-parse", "7625f8c"], cwd=ROOT).decode().strip()
    pins = {}
    for folder in ("src/asof", "paper/release/code/src/asof_p05_replay"):
        for path in sorted((ROOT / folder).rglob("*")):
            if path.is_file() and path.suffix in (".py", ".json"):
                rel = path.relative_to(ROOT).as_posix()
                prior = subprocess.check_output(["git", "show", commit + ":" + rel], cwd=ROOT)
                assert path.read_bytes() == prior
                pins[rel] = {"sha256": sha(prior), "bytes": len(prior)}
    for name in ("pyproject.toml", "uv.lock", "LICENSE", "data/catalog/sources.json",
                 "paper/manuscript.md", "paper/supplement.md", "paper/README.md",
                 "paper/RELATED-WORK-SOURCE-AUDIT.md", "paper/references.bib", "paper/references.json",
                 "paper/asof-source-reporting-preprint.pdf", "paper/PDF-BUILD.json",
                 "paper/asof-source-reporting-preprint-v2.pdf", "paper/PDF-BUILD-v2.json",
                 "paper/release/RELEASE-RECORD.json", "paper/release/qualification.json",
                 "paper/release/WORKING-PACKET-RECORD.json", "paper/release/WORKING-PACKET-QUALIFICATION.json"):
        prior = subprocess.check_output(["git", "show", commit + ":" + name], cwd=ROOT)
        pins[name] = {"sha256": sha(prior), "bytes": len(prior)}
    external = {}
    for name, expected in (
        ("data/cache/p09-runtime-bundle-20261101T213500Z/protocol.json", "e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529"),
        ("data/derived/preprint-p09-release-20261101T232900Z/asof-research-artifact-0.1.0.zip", "f4d7ab4bb1a0b79c0ecadbac15891f4cc2925abe624298e8a48a762190b6782e"),
        ("data/derived/preprint-p10-packet-20261101T235000Z/asof-working-paper-v2.zip", "e5c9478c9a55ac6e5c9b3ddfb809b84407cb7876ae1ec28887e19f2b1af88433"),
    ):
        raw = (ROOT / name).read_bytes()
        assert sha(raw) == expected
        external[name] = {"sha256": expected, "bytes": len(raw)}
    result = {"schema_version": 1, "method": "tether.rename_baseline.v1",
        "status": "PASS_PRE_RENAME_IDENTITY_BASELINE", "pre_rename_commit": commit,
        "role": "evaluation_only", "agent_visible": False, "pins": pins, "sealed_artifacts": external,
        "legacy_core_and_replay_payloads": 100, "provider_originals_read": 0,
        "scientific_change": False, "publication_authorized": False}
    assert len([p for p in pins if p.startswith(("src/asof/", "paper/release/code/src/asof_p05_replay/"))]) == 100
    target = HERE / "PRE-RENAME-BASELINE.json"
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "pinned_files": len(pins), "sealed_artifacts": len(external)}))


if __name__ == "__main__":
    main()
