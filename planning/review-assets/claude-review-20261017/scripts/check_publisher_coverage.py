"""Does the local Open Targets 25.09 selection cover every non-ChEMBL evidence part, every target part and the
disease part in the publisher's file list? Compares the 2,206-file manifest (inspection.json) with the publisher's
`release_data_integrity`. Pass the list's path as the first argument or let the script download it (3 MB).
Stdlib only. Prints JSON.
"""
import collections
import json
import sys
import tempfile
import urllib.request
from pathlib import Path

URL = "https://ftp.ebi.ac.uk/pub/databases/opentargets/platform/25.09/release_data_integrity"
INSPECTION = r"D:\Projects\drug_target_agents\data\derived\literature-coverage-20261017T082208Z\inspection.json"
if len(sys.argv) > 1:
    listing = Path(sys.argv[1]).read_text(encoding="utf-8")
else:
    listing = urllib.request.urlopen(URL, timeout=120).read().decode("utf-8")
publisher = {}
for line in listing.splitlines():
    if line.strip():
        digest, path = line.split(None, 1)
        publisher[path.strip().lstrip("./")] = digest

files = json.loads(Path(INSPECTION).read_bytes().decode("utf-8-sig"))["files"]
prefix = "raw/open_targets_platform/25.09/"


def to_publisher_path(path):
    rel = path[len(prefix):]
    if rel.startswith("supplemental-20261017T064802Z/europepmc/"):
        rel = "output/evidence/sourceId=europepmc/" + rel.rsplit("/", 1)[1]
    return rel


local = {to_publisher_path(f["source"]["path"]) for f in files if f["source"]["path"].startswith(prefix)}
report = {}
for name, directory in (("evidence", "output/evidence/"), ("target", "output/target/"), ("disease", "output/disease/")):
    listed = {p for p in publisher if p.startswith(directory) and "sourceId=chembl" not in p}
    report[name] = {"publisher_files_excluding_chembl": len(listed),
                    "present_locally": len(listed & local),
                    "absent": sorted(listed - local),
                    "local_not_in_publisher_list": sorted(p for p in local if p.startswith(directory)
                                                           and p not in listed)}
report["publisher_chembl_evidence_files_excluded_by_design"] = sum(
    1 for p in publisher if p.startswith("output/evidence/") and "sourceId=chembl" in p)
report["evidence_sources"] = len({p.split("/")[2] for p in publisher if p.startswith("output/evidence/")})
print(json.dumps(report, indent=1))
