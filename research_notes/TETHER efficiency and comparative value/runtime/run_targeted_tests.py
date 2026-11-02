"""Run existing fictional suites with every temporary fixture under audit cache."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[3]
output=Path(sys.argv[1]).absolute(); output.mkdir(parents=True,exist_ok=False)
temporary=output/"fixtures"; temporary.mkdir()
os.environ["TMP"]=os.environ["TEMP"]=str(temporary)
tempfile.tempdir=str(temporary)
original=tempfile.TemporaryDirectory
def relocated(*args,**kwargs):
    kwargs["dir"]=temporary
    return original(*args,**kwargs)
tempfile.TemporaryDirectory=relocated
sys.path.insert(0,str(ROOT))
modules=[*sorted((ROOT/"packages/tether/tests").glob("test_*.py")), *[ROOT/"tests"/name for name in (
    "test_backend_hardening.py","test_runtime_hardening_peer.py","test_store_temporal_hardening.py",
    "test_study_source_fact_sources.py","test_study_source_fact_peer.py","test_study_source_fact_reporting.py",
    "test_v02_ingest.py","test_local_model.py")]]
if len(sys.argv)>2:
    modules=[path for path in modules if path.name in sys.argv[2:]]
suite=unittest.TestSuite()
for i,path in enumerate(modules):
    spec=importlib.util.spec_from_file_location("runtime_audit_test_"+str(i),path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
with (output/"tests.log").open("w",encoding="utf-8") as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
report=dict(testsRun=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
    success=result.wasSuccessful(),interpreter=sys.executable,modules=[str(path.relative_to(ROOT)) for path in modules])
(output/"results.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report,indent=2));sys.exit(0 if result.wasSuccessful() else 1)
