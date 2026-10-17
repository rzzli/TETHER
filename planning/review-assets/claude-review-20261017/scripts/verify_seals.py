"""Independent re-hash of sealed evidence manifests (written for the review; does not import project code)."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Projects\drug_target_agents")
COHORTS = ROOT / "data" / "benchmark" / "cohorts"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    overall = {}
    for manifest_path in sorted(COHORTS.glob("*/evidence-manifest.json")):
        directory = manifest_path.parent
        manifest = json.loads(manifest_path.read_bytes().decode("utf-8-sig"))
        listed = {}
        problems = []
        for entry in manifest["files"]:
            rel = entry["path"].replace("\\", "/")
            listed[rel] = entry
            target = directory / rel
            if not target.is_file():
                problems.append(("missing", rel))
                continue
            size = target.stat().st_size
            if size != entry["bytes"]:
                problems.append(("size", rel, entry["bytes"], size))
                continue
            digest = sha256(target)
            if digest != entry["sha256"]:
                problems.append(("hash", rel, entry["sha256"], digest))
        # Files present on disk but not sealed (excluding the manifest itself and caches).
        on_disk = {
            p.relative_to(directory).as_posix()
            for p in directory.rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        }
        extra = sorted(on_disk - set(listed) - {"evidence-manifest.json"})
        overall[directory.name] = {
            "manifest_sha256": sha256(manifest_path),
            "listed": len(listed),
            "on_disk": len(on_disk),
            "problems": problems,
            "unsealed_files": extra[:25],
            "unsealed_count": len(extra),
        }
        # Parent chain, if present.
        for parent in manifest.get("parents", []):
            parent_dir = ROOT / parent["path"].replace("\\", "/")
            parent_manifest = parent_dir / "evidence-manifest.json"
            actual = sha256(parent_manifest) if parent_manifest.is_file() else None
            overall[directory.name].setdefault("parents", []).append(
                {"path": parent["path"], "claimed": parent["sha256"], "actual": actual,
                 "match": actual == parent["sha256"], "files_verified_claim": parent.get("files_verified")}
            )
    print(json.dumps(overall, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
