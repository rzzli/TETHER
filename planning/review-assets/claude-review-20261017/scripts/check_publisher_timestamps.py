"""Sample publisher-side Last-Modified headers for the selected Open Targets 25.09 files.

Question: can a publisher-side timestamp bound the first-public date of the 25.09 files (the project currently stores
only its own 2026-10-11 download receipts)? HEAD requests only; no data are downloaded. Stdlib only.
Usage: python check_publisher_timestamps.py [sample_size]   (default 200; use 0 for all 2,205 files)
"""
import collections
import json
import random
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime

INSPECTION = r"D:\Projects\drug_target_agents\data\derived\literature-coverage-20261017T082208Z\inspection.json"
BASE = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/"
SUPPLEMENTAL = "supplemental-20261017T064802Z/europepmc/"
PREFIX = "raw/open_targets_platform/25.09/"

files = json.loads(open(INSPECTION, "rb").read().decode("utf-8-sig"))["files"]
rels = []
for entry in files:
    path = entry["source"]["path"]
    if not path.startswith(PREFIX):
        continue
    rel = path[len(PREFIX):]
    if rel.startswith(SUPPLEMENTAL):
        rel = "output/evidence/sourceId=europepmc/" + rel.rsplit("/", 1)[1]
    rels.append(rel)
size = int(sys.argv[1]) if len(sys.argv) > 1 else 200
random.seed(20261017)
sample = rels if size == 0 else random.sample(rels, min(size, len(rels)))


def head(rel):
    request = urllib.request.Request(BASE + rel.replace("=", "%3D"), method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return rel, response.status, response.headers.get("Last-Modified")
    except Exception as error:  # record failures; they are not evidence either way
        return rel, None, f"ERROR {type(error).__name__}"


with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(head, sample))
stamps = []
errors = []
for rel, status, modified in results:
    if status == 200 and modified:
        stamps.append(parsedate_to_datetime(modified))
    else:
        errors.append((rel, status, modified))
by_day = collections.Counter(s.date().isoformat() for s in stamps)
print(json.dumps({"files_in_selection": len(rels), "sampled": len(sample), "ok": len(stamps), "errors": errors[:5],
                  "error_count": len(errors), "earliest": min(stamps).isoformat() if stamps else None,
                  "latest": max(stamps).isoformat() if stamps else None,
                  "distinct_days": dict(sorted(by_day.items()))}, indent=1))
