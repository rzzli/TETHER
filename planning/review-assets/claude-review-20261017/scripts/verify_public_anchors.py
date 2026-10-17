"""Walk every JSON under data/manifests/public, find {path|workspace_path, sha256} pairs, re-hash the target."""
import hashlib
import json
from pathlib import Path

ROOT = Path(r"D:\Projects\drug_target_agents")
PUBLIC = ROOT / "data" / "manifests" / "public"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk(node, found):
    if isinstance(node, dict):
        path = node.get("path") or node.get("workspace_path")
        digest = node.get("sha256")
        if isinstance(path, str) and isinstance(digest, str) and len(digest) == 64:
            found.append((path, digest))
        for value in node.values():
            walk(value, found)
    elif isinstance(node, list):
        for value in node:
            walk(value, found)


summary = {}
for manifest in sorted(PUBLIC.glob("*.json")):
    data = json.loads(manifest.read_bytes().decode("utf-8-sig"))
    found = []
    walk(data, found)
    row = {"pairs": len(found), "ok": 0, "missing": [], "mismatch": [], "external_or_absolute": []}
    for path, digest in found:
        normalized = path.replace("\\", "/")
        if ":" in normalized.split("/")[0]:  # absolute path (e.g., E:/...)
            target = Path(normalized)
        else:
            target = ROOT / normalized
        if not target.exists():
            row["missing"].append(path)
        elif target.is_dir():
            row["external_or_absolute"].append(path)
        else:
            actual = sha256(target)
            if actual == digest:
                row["ok"] += 1
            else:
                row["mismatch"].append({"path": path, "claimed": digest[:12], "actual": actual[:12]})
    summary[manifest.name] = row

print(json.dumps(summary, indent=1))
