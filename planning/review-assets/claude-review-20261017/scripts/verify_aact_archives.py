"""Re-hash the six AACT archives under raw/aact_snapshots and compare with the recorded SHA-256 values.

Expected values come from data/manifests/public (five restored dates) and the optional-2026 archive check.
Stdlib only. Takes about 4 minutes (12.9 GB). Prints JSON.
"""
import hashlib
import json
import os
import time

ROOT = r"E:\projects_data\drug_target_agents_data\raw\aact_snapshots"
EXPECTED = {
    "0e7c54e6e7214ac7bd31da20960e1a9ce8590b18b87a9661b414f5b1c76cf1d1": ("2023-01-01", 3194237475),
    "b2f638dad976c9715fbf9a40bc01d37b178b915c070bc66bc38ffc4f861723ee": ("2023-07-02", 1678107214),
    "d072ff26df506537a156bdb853bfdc6312a59561d8d085959d1865e33aee394d": ("2024-01-01", 1769509083),
    "ea1af6b9846a919dfe229d9a97d344eefa16c663a3b6c34b639b0d0432fe37e8": ("2024-07-01", 1840640346),
    "53bb8d15d3bc902659f2f64985af4636679d1208eac1f143d96aa42d7f2ef297": ("2025-01-01", 2105000060),
    "7fb923dacecae1dfec864c3e21fbed669add8a64b6bd1664ce973c24a514035c": ("2026-01-01 (optional, not restored)", 2344676979),
}

started = time.time()
found = {}
for directory, _, names in os.walk(ROOT):
    for name in names:
        if not name.lower().endswith(".zip"):
            continue
        path = os.path.join(directory, name)
        digest, size = hashlib.sha256(), 0
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 24), b""):
                digest.update(chunk)
                size += len(chunk)
        found[digest.hexdigest()] = (path, size)

report = {"archives_hashed": len(found), "elapsed_seconds": round(time.time() - started, 1), "results": []}
for sha, (label, size) in EXPECTED.items():
    hit = found.get(sha)
    report["results"].append({"snapshot": label, "expected_bytes": size,
                              "match": bool(hit and hit[1] == size), "path": hit[0] if hit else None})
report["unexpected_archives"] = [path for sha, (path, _) in found.items() if sha not in EXPECTED]
report["total_bytes"] = sum(size for _, size in found.values())
print(json.dumps(report, indent=1))
