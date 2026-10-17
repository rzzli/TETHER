"""Compare local SHA-1 of every selected Open Targets 25.09 file to the publisher's release_data_integrity list."""
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(r"D:\Projects\drug_target_agents")
RAW = Path(r"E:\projects_data\drug_target_agents_data")
URL = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/release_data_integrity"
if len(sys.argv) > 1:
    PUB = Path(sys.argv[1])
else:  # fetch the publisher list (3 MB) next to the temp directory and check it against the publisher's own .sha1
    import tempfile
    import urllib.request
    PUB = Path(tempfile.mkdtemp(prefix="ot25-integrity-")) / "release_data_integrity"
    data = urllib.request.urlopen(URL, timeout=120).read()
    PUB.write_bytes(data)
    expected = urllib.request.urlopen(URL + ".sha1", timeout=60).read().split()[0].decode()
    assert hashlib.sha1(data).hexdigest() == expected, "publisher list does not match its .sha1"
inspection = json.loads((ROOT / "data/derived/literature-coverage-20261017T082208Z/inspection.json").read_bytes().decode("utf-8-sig"))

publisher = {}
for line in PUB.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    digest, path = line.split(None, 1)
    publisher[path.strip().lstrip("./")] = digest

prefix = "raw/open_targets_platform/25.09/"
jobs = []
for f in inspection["files"]:
    p = f["source"]["path"]
    if p.startswith(prefix):
        rel = p[len(prefix):]
        if rel.startswith("supplemental-20261017T064802Z/europepmc/"):
            # Separately downloaded Europe PMC partitions: publisher path is the evidence sourceId directory.
            rel = "output/evidence/sourceId=europepmc/" + rel.rsplit("/", 1)[1]
        jobs.append((p, rel))


def check(job):
    local_rel, pub_rel = job
    expected = publisher.get(pub_rel)
    if expected is None:
        return local_rel, "not_listed_by_publisher", None
    h = hashlib.sha1()
    with (RAW / local_rel.replace("/", "\\")).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 22), b""):
            h.update(chunk)
    return local_rel, ("match" if h.hexdigest() == expected else "MISMATCH"), expected


start = time.monotonic()
with ThreadPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(check, jobs))
summary = {
    "ot25_files_in_manifest": len(jobs),
    "publisher_entries": len(publisher),
    "match": sum(r[1] == "match" for r in results),
    "mismatch": [r[0] for r in results if r[1] == "MISMATCH"],
    "not_listed": [r[0] for r in results if r[1] == "not_listed_by_publisher"],
    "elapsed_seconds": round(time.monotonic() - start, 1),
}
print(json.dumps(summary, indent=1))
