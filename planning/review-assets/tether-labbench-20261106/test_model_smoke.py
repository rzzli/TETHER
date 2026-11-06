"""Qualification of smoke orchestration; fictional mocks and tiny non-model processes only."""
import ctypes
import importlib.util
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("labbench_smoke",HERE/"model_smoke.py")
smoke=importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class SmokeTests(unittest.TestCase):
    def test_fixture_is_native_and_source_has_verified_text_hash(self):
        query,sources,expected=smoke.fixture()
        from experiments.labbench.native_contract import validate_query,validate_prediction
        validate_query(query)
        validate_prediction(expected,query,[s["source_id"] for s in sources])
        self.assertEqual(sources[0]["sha256"],smoke.sha(sources[0]["text"].encode()))
        self.assertEqual(set(query),{"id","question","choices"})

    def test_external_code_pin_failure_never_reserves_or_dispatches(self):
        with tempfile.TemporaryDirectory(dir=smoke.ROOT/"data/cache") as folder:
            output=Path(folder)/"attempt"
            with patch.object(smoke,"supervise_command") as run, self.assertRaises(smoke.ContractError):
                smoke.execute(output,{})
            self.assertFalse(output.exists());run.assert_not_called()

    def test_worker_failure_is_retained_without_retry(self):
        with tempfile.TemporaryDirectory(dir=smoke.ROOT/"data/cache") as folder:
            output=Path(folder)/"attempt"
            with patch.object(sys,"pycache_prefix",str(Path(folder)/"parent-cache")), \
                    patch.object(smoke,"supervise_command",side_effect=TimeoutError("fictional timeout")) as run, \
                    self.assertRaises(TimeoutError):
                smoke.execute(output,smoke.code_pins())
            self.assertEqual(run.call_count,1)
            failure=smoke.parse_json((output/"FAILURE.json").read_bytes())
            self.assertEqual(failure["status"],"failed")
            self.assertFalse(failure["automatic_retry"])
            with patch.object(sys,"pycache_prefix",str(Path(folder)/"parent-cache")), self.assertRaises(FileExistsError):
                smoke.execute(output,smoke.code_pins())

    @unittest.skipUnless(sys.platform=="win32","Windows job semantics")
    def test_parent_deadline_closes_job_and_terminates_nonmodel_descendant(self):
        with tempfile.TemporaryDirectory(dir=smoke.ROOT/"data/cache") as folder:
            proof=Path(folder)/"containment.json"
            command=[sys.executable,"-I","-B","-X","pycache_prefix="+str(Path(folder)/"child-cache"),
                     str(HERE/"model_smoke.py"),"--containment-fixture",str(proof)]
            result=None
            try:
                result=smoke.supervise_command(command,limits=smoke.ProcessLimits(timeout_seconds=2,max_output_bytes=65536))
            except smoke.ContractError as error:
                result=getattr(error,"tether_engine_result",None)
            self.assertIsNotNone(result)
            self.assertTrue(proof.is_file(),result.stderr.decode(errors="replace"))
            info=smoke.parse_json(proof.read_bytes())
            self.assertTrue(info["contained"])
            self.assertNotEqual(result.returncode,0)
            from ctypes import wintypes as w
            api=ctypes.WinDLL("kernel32",use_last_error=True)
            api.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];api.OpenProcess.restype=w.HANDLE
            api.GetExitCodeProcess.argtypes=[w.HANDLE,ctypes.POINTER(w.DWORD)];api.GetExitCodeProcess.restype=w.BOOL
            api.CloseHandle.argtypes=[w.HANDLE]
            alive=True
            for _ in range(20):
                handle=api.OpenProcess(0x1000,False,info["child_pid"])
                if not handle:
                    alive=False;break
                code=w.DWORD()
                try:
                    self.assertTrue(api.GetExitCodeProcess(handle,ctypes.byref(code)))
                    alive=code.value==259
                finally:
                    api.CloseHandle(handle)
                if not alive:break
                time.sleep(.05)
            self.assertFalse(alive,"Owned non-model descendant survived parent deadline/job closure")


if __name__=="__main__":unittest.main()
