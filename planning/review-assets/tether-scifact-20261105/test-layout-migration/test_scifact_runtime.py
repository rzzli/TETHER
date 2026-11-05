import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from asof.serde import ContractError
from experiments.scifact.runtime import load_input, measured

ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def child(self, code, output, timeout=15):
        prefix = f"import sys;sys.path.insert(0,{str(ROOT)!r});\n"
        return subprocess.run([sys.executable, '-I', '-B', '-c', prefix+code], cwd=ROOT,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)

    def test_resource_schema_has_native_measurements_without_tokens(self):
        import time
        from experiments.scifact.tether_adapter import validate_resources
        value = measured(time.perf_counter(), time.process_time(), input_bytes=4, output_bytes=5, examples=1)
        validate_resources(value)
        self.assertIsNone(value['model_input_tokens'])
        self.assertEqual(value['provider_cost_usd'], 0)

    def test_explicit_file_hash_is_required(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';p.write_bytes(b'x')
            with self.assertRaises(ContractError):
                load_input({'path':str(p),'bytes':1,'sha256':'0'*64})

    def test_worker_denies_undeclared_reference_and_retains_attempt(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/'out';out.mkdir()
            secret=Path(d)/'reference';secret.write_bytes(b'not-an-answer')
            code=f'''from pathlib import Path
from experiments.scifact.runtime import IOAudit
a=IOAudit([],Path({str(out)!r}),[]);a.activate()
try: Path({str(secret)!r}).read_bytes()
except PermissionError: pass
else: raise AssertionError('undeclared reference admitted')
a.flush()
'''
            result=self.child(code,out)
            self.assertEqual(result.returncode,0,result.stderr.decode())
            rows=[json.loads(x) for x in (out/'io-audit.jsonl').read_text().splitlines()]
            self.assertTrue(any(not r['allowed'] and r['path']==str(secret.resolve()) for r in rows))

    def test_watchdog_stops_stalled_call_without_completing_it(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            code=f'''import time
from experiments.scifact.runtime import Watchdog
with Watchdog({str(out)!r},call_seconds=0.05,sample_seconds=0.02) as w:
    w.active_started=time.perf_counter()
    time.sleep(5)
raise AssertionError('deadline was ignored')
'''
            result=self.child(code,out)
            self.assertEqual(result.returncode,124,result.stderr.decode())
            self.assertEqual(json.loads((out/'WATCHDOG-STOP.json').read_text())['reason'],'call_deadline_observed')

    @unittest.skipUnless(os.name=='nt','Windows memory counter qualification')
    def test_observed_memory_ceiling_stops_worker(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            code=f'''import time
from experiments.scifact.runtime import Watchdog
with Watchdog({str(out)!r},memory_limit=1,sample_seconds=0.02):time.sleep(5)
'''
            result=self.child(code,out)
            self.assertEqual(result.returncode,125,result.stderr.decode())
            self.assertEqual(json.loads((out/'WATCHDOG-STOP.json').read_text())['reason'],'memory_limit_observed')


if __name__=='__main__':unittest.main()
