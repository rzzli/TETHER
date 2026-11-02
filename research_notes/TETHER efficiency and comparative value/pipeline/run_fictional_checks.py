"""Retain focused existing fictional tests without invoking their artifact writers."""
from __future__ import annotations
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/"data/cache/comparative-audit-20261102/pipeline-attempt-02"
sys.path.insert(0,str(ROOT))

class RetainedTemporaryDirectory(tempfile.TemporaryDirectory):
    def cleanup(self):
        self._finalizer.detach()

def module(name, relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    mod=importlib.util.module_from_spec(spec)
    sys.modules[name]=mod
    spec.loader.exec_module(mod)
    return mod

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    tempfile.tempdir=str(OUT)
    suite=unittest.defaultTestLoader.loadTestsFromNames([
        "tests.test_validation_failure_report", "tests.test_validation_live_errors", "tests.test_tether_policy_import"])
    receipt=module("pipeline_receipt_tests","planning/review-assets/full-project-review-20261102/data/test_download_verifier.py")
    packet=module("pipeline_packet_tests","planning/review-assets/tether-q06-20261102/test_packet_v2.py")
    packet.ROOT=OUT/"packet-workspace"
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(receipt.ReceiptIdentityTests))
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(packet.PacketTests))
    transcript=io.StringIO()
    with patch.object(tempfile,"TemporaryDirectory",RetainedTemporaryDirectory):
        result=unittest.TextTestRunner(stream=transcript,verbosity=2).run(suite)
    (OUT/"transcript.txt").write_text(transcript.getvalue(),encoding="utf-8")
    report=dict(status="PASS" if result.wasSuccessful() else "FAIL",tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
        scope="Existing fictional validation, receipt identity, catalog importer and current v2 packet tests only; no real archive/PDF/source build",fixture_directories_retained=True)
    (OUT/"result.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2))
    return int(not result.wasSuccessful())

if __name__=="__main__":
    raise SystemExit(main())
