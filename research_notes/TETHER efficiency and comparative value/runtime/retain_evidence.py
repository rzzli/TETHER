"""Retain small audit records; capture narrow installed witness verification."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[3]
out=Path(__file__).parent/"evidence-v1";out.mkdir()
cache=ROOT/"data/cache/comparative-audit-20261102"
for source,name in (
    ("runtime-probe-v1/results.json","policy-and-hash-probes.json"),
    ("runtime-mechanics-v1/results.json","accounting-and-compiler-probes.json"),
    ("runtime-tests-v1/results.json","core-tests-initial.json"),
    ("runtime-tests-v1/tests.log","core-tests-initial.log"),
    ("runtime-tests-harness-correction-v2/results.json","core-tests-correction.json"),
    ("runtime-tests-harness-correction-v2/tests.log","core-tests-correction.log"),
    ("runtime-ingest-optional-v1/results.json","optional-tests.json"),
    ("runtime-ingest-optional-v1/tests.log","optional-tests.log")):
    shutil.copyfile(cache/source,out/name)
python=ROOT/"data/cache/tether-050-qualified-build/env/Scripts/python.exe"
root=cache/"runtime-probe-v1"
verify=[str(python),"-I","-B","-m","tether","verify","--run-dir",str(root/"unused-future-receipt/outer"),
    "--receipt-sha256","70180cc79778d85a4c3eacdc4c75d64884549d1002f858ebc8dd24a92445df53"]
f=root/"referenced-future-receipt"
deny=[str(python),"-I","-B","-m","tether","run","--case",str(f/"case.json"),"--snapshot",str(f/"normalized/snapshot.json"),
    "--catalog",str(f/"data/catalog/sources.json"),"--catalog-policy",str(f/"policy.json"),"--policy-roots",str(f/"roots.json"),
    "--policy-use","fictional-use","--policy-frame-sha256","f"*64,"--output",str(f/"outer-negative-v1")]
results=[]
for argv in (verify,deny):
    completed=subprocess.run(argv,cwd=ROOT,capture_output=True,text=True,timeout=60)
    results.append(dict(argv=argv,returncode=completed.returncode,stdout=completed.stdout,stderr=completed.stderr))
(out/"installed-witness.json").write_text(json.dumps(results,indent=2),encoding="utf-8")
print(json.dumps([dict(returncode=r["returncode"],stdout_bytes=len(r["stdout"].encode()),stderr=r["stderr"]) for r in results],indent=2))
