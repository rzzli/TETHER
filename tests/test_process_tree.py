"""Finite candidate tests; synthetic Python processes only, no model or network."""
import ctypes
from concurrent.futures import ThreadPoolExecutor
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from tether_engine.process_tree import WindowsJob

import tether_engine

HERE = Path(tether_engine.__file__).resolve().parent.parent
if os.name == 'nt':
    K = ctypes.WinDLL('kernel32',use_last_error=True)
    K.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    K.OpenProcess.restype=wintypes.HANDLE
    K.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
    K.WaitForSingleObject.restype=wintypes.DWORD
    K.CloseHandle.argtypes=[wintypes.HANDLE]
    K.CloseHandle.restype=wintypes.BOOL

TREE_SCRIPT = ('import subprocess,sys,json,time;from pathlib import Path;'
    'p=subprocess.Popen([sys.executable,"-I","-B","-S","-c","import time;time.sleep(30)"],creationflags=0x08000000);'
    'Path(sys.argv[1]).write_text(json.dumps({"grandchild":p.pid}));time.sleep(30)')

@unittest.skipUnless(os.name == 'nt', 'Windows Job Object qualification')
class WindowsJobTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
    def wait_file(self,path):
        end=time.monotonic()+5
        while not path.exists() and time.monotonic()<end:time.sleep(.01)
        self.assertTrue(path.exists())
    def hold(self,pid):
        handle=K.OpenProcess(0x100000,False,pid)
        if not handle:raise ctypes.WinError(ctypes.get_last_error())
        self.addCleanup(K.CloseHandle,handle)
        return handle
    def tree(self):
        job=WindowsJob()
        self.addCleanup(job.close)
        p=job.launch([sys.executable,'-I','-B','-S','-c',TREE_SCRIPT,str(self.root/'child.json')],
            deadline=time.monotonic()+5,stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        self.addCleanup(lambda:p.wait(timeout=5) if p.poll() is not None else (job.terminate(),p.wait(timeout=5)))
        self.wait_file(self.root/'child.json')
        child=json.loads((self.root/'child.json').read_text())['grandchild']
        return job,p,self.hold(child)
    def test_finite_success_and_one_use(self):
        job=WindowsJob();self.addCleanup(job.close)
        p=job.launch([sys.executable,'-I','-B','-S','-c','print("fixture")'],
                     deadline=time.monotonic()+5,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        out,err=p.communicate(timeout=5)
        self.assertEqual(out.strip(),b'fixture');self.assertEqual(p.returncode,0)
        counts=[];close=job._close
        def checked_close(handle):
            if handle==job._handle:counts.append(job.active_processes())
            return close(handle)
        with patch.object(job,'_close',side_effect=checked_close):
            job.finish(time.monotonic()+3)
        self.assertEqual(counts,[0])
        with self.assertRaises(RuntimeError):job.launch([],deadline=time.monotonic()+3)
    def test_assignment_failure_prevents_execution(self):
        job=WindowsJob();self.addCleanup(job.close)
        marker=self.root/'must-not-exist'
        command=[sys.executable,'-I','-B','-S','-c','from pathlib import Path;import sys;Path(sys.argv[1]).touch()',str(marker)]
        with patch.object(job,'_assign',side_effect=PermissionError('fixture assignment refusal')):
            with self.assertRaisesRegex(PermissionError,'fixture assignment refusal'):
                job.launch(command,deadline=time.monotonic()+5)
        self.assertFalse(marker.exists())
        self.assertIsNotNone(job.process.returncode)
    def test_resume_interruption_cleans_suspended_process(self):
        job=WindowsJob();self.addCleanup(job.close)
        with patch.object(job,'_resume_initial_thread',side_effect=KeyboardInterrupt('fixture interruption')):
            with self.assertRaises(KeyboardInterrupt):
                job.launch([sys.executable,'-I','-B','-S','-c','raise SystemExit(0)'],deadline=time.monotonic()+5)
        self.assertIsNotNone(job.process.returncode)
    def test_finish_stops_root_and_inherited_grandchild(self):
        job,p,child=self.tree()
        self.assertGreaterEqual(job.active_processes(),2)
        job.finish(time.monotonic()+3)
        p.wait(timeout=3)
        self.assertEqual(K.WaitForSingleObject(child,3000),0)
    def test_closing_job_stops_root_and_grandchild(self):
        job,p,child=self.tree()
        job.close()
        p.wait(timeout=3)
        self.assertEqual(K.WaitForSingleObject(child,3000),0)
    def test_owner_abrupt_exit_closes_job_and_stops_descendants(self):
        script='''import os,sys,time,json,subprocess
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from tether_engine.process_tree import WindowsJob
root=Path(sys.argv[2]);job=WindowsJob()
code=sys.argv[3]
p=job.launch([sys.executable,'-I','-B','-S','-c',code,str(root/'child.json')],deadline=time.monotonic()+5,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
while not (root/'child.json').exists():time.sleep(.01)
(root/'root.json').write_text(json.dumps({'pid':p.pid}))
while not (root/'exit').exists():time.sleep(.01)
os._exit(23)
'''
        owner=subprocess.Popen([sys.executable,'-I','-B','-S','-c',script,str(HERE),str(self.root),TREE_SCRIPT],
            creationflags=0x08000000,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            self.wait_file(self.root/'root.json')
            root_handle=self.hold(json.loads((self.root/'root.json').read_text())['pid'])
            child=self.hold(json.loads((self.root/'child.json').read_text())['grandchild'])
            (self.root/'exit').touch()
            self.assertEqual(owner.wait(timeout=5),23)
            self.assertEqual(K.WaitForSingleObject(root_handle,3000),0)
            self.assertEqual(K.WaitForSingleObject(child,3000),0)
        finally:
            if owner.poll() is None:owner.kill()
            owner.wait(timeout=5)

    def test_wrapper_finishes_descendants_after_root_exits(self):
        from tether._process import supervise_command, ProcessLimits
        # Hold a synchronization handle while the owned child is still alive;
        # check termination without relying on PID lookup after cleanup.
        marker, release = self.root/'wrapper-child.json', self.root/'release'
        script = '''import subprocess,sys,time,json
from pathlib import Path
p=subprocess.Popen([sys.executable,'-I','-B','-S','-c','import time;time.sleep(5)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
Path(sys.argv[1]).write_text(json.dumps({'pid':p.pid}))
while not Path(sys.argv[2]).exists():time.sleep(.01)
'''
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(supervise_command,
                [sys.executable,'-I','-B','-S','-c',script,str(marker),str(release)],
                limits=ProcessLimits(5,4096))
            try:
                self.wait_file(marker)
                handle = self.hold(json.loads(marker.read_text())['pid'])
            finally:
                release.touch()
            result = future.result(timeout=6)
        try:
            self.assertEqual(result.returncode,0)
            self.assertEqual(K.WaitForSingleObject(handle,100),0,
                             'Successful wrapper left an inherited descendant alive')
        finally:
            K.WaitForSingleObject(handle,6000)  # Finite fixture exits itself on pre-fix failure.

    def test_tokenizer_finishes_descendants_after_root_exits(self):
        from tether_engine.journal import RunJournal
        from tether_engine.study.tokenization import _run_child
        marker, release = self.root/'token-child.json', self.root/'release'
        script = '''import subprocess,sys,time,json
from pathlib import Path
sys.stdin.buffer.read()
p=subprocess.Popen([sys.executable,'-I','-B','-S','-c','import time;time.sleep(5)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
Path(sys.argv[1]).write_text(json.dumps({'pid':p.pid}))
while not Path(sys.argv[2]).exists():time.sleep(.01)
print('fixture')
'''
        journal = RunJournal(self.root/'token-output',kind='build')
        self.addCleanup(journal.close)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_child,
                [sys.executable,'-I','-B','-S','-c',script,str(marker),str(release)],
                b'fixture',time.monotonic()+10,journal.output,journal)
            try:
                self.wait_file(marker)
                handle = self.hold(json.loads(marker.read_text())['pid'])
            finally:
                release.touch()
            result = future.result(timeout=12)
        try:
            self.assertEqual(result['exit_code'],0)
            self.assertEqual(K.WaitForSingleObject(handle,100),0,
                             'Successful tokenizer left an inherited descendant alive')
        finally:
            K.WaitForSingleObject(handle,6000)

    def test_server_stops_descendants_on_normal_context_exit(self):
        from tether_engine.journal import RunJournal
        from tether_engine.study.process import OwnedServer, ServerSpec
        from tether_engine.study.proofs import capture_file
        marker = self.root/'server-child.json'
        script = '''import subprocess,sys,time,json
from pathlib import Path
p=subprocess.Popen([sys.executable,'-I','-B','-S','-c','import time;time.sleep(5)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
Path(sys.argv[1]).write_text(json.dumps({'pid':p.pid}))
time.sleep(5)
'''
        executable = Path(sys.executable).absolute()
        proof = capture_file(executable,'python-fixture')
        spec = ServerSpec((str(executable),'-I','-B','-S','-c',script,str(marker)),
                          proof,(),'127.0.0.1',55581,5,1,1)
        journal = RunJournal(self.root/'server-output',kind='build')
        self.addCleanup(journal.close)
        server = OwnedServer(spec,bindings={'python-fixture':executable},output=journal.output,
                             journal=journal,listener_owner=lambda *args:True,
                             health_probe=lambda *args:marker.exists(),availability_probe=lambda *args:None)
        with server:
            handle = self.hold(json.loads(marker.read_text())['pid'])
        try:
            self.assertTrue(server.terminal_record['server_stopped'])
            self.assertEqual(K.WaitForSingleObject(handle,100),0,
                             'Server shutdown left an inherited descendant alive')
        finally:
            K.WaitForSingleObject(handle,6000)

    def test_real_entrypoints_contain_descendants_after_owner_abrupt_exit(self):
        source = Path(__file__).resolve().parents[1]
        self.check_abrupt_entrypoints(("wrapper", "tokenizer", "server"),
                                     source / "src", source / "packages/tether/src")

    def test_installed_wrapper_contains_descendants_after_owner_abrupt_exit(self):
        import tether
        self.check_abrupt_entrypoints(("wrapper",), HERE,
                                     Path(tether.__file__).resolve().parent.parent)

    def check_abrupt_entrypoints(self, modes, engine_root, wrapper_root):
        script = '''import os,sys,time,threading,subprocess,json
from pathlib import Path
sys.path[:0]=[sys.argv[1],sys.argv[2]]
root=Path(sys.argv[3]);mode=sys.argv[4]
def exit_on_signal():
    end=time.monotonic()+15
    while time.monotonic()<end and not (root/'exit').exists():time.sleep(.01)
    os._exit(23)
threading.Thread(target=exit_on_signal,daemon=True).start()
code="""import subprocess,sys,time,json,os
from pathlib import Path
p=subprocess.Popen([sys.executable,'-I','-B','-S','-c','import time;time.sleep(15)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
Path(sys.argv[1]).write_text(json.dumps({'pid':os.getpid(),'grandchild':p.pid}))
time.sleep(15)
"""
argv=[sys.executable,'-I','-B','-S','-c',code,str(root/'tree.json')]
if mode=='wrapper':
    from tether._process import supervise_command,ProcessLimits
    supervise_command(argv,limits=ProcessLimits(20,4096))
else:
    from tether_engine.journal import RunJournal
    journal=RunJournal(root/'output',kind='build')
    if mode=='tokenizer':
        from tether_engine.study.tokenization import _run_child
        _run_child(argv,b'fixture',time.monotonic()+20,journal.output,journal)
    else:
        from tether_engine.study.process import OwnedServer,ServerSpec
        from tether_engine.study.proofs import capture_file
        proof=capture_file(Path(sys.executable),'python-fixture')
        spec=ServerSpec(tuple(argv),proof,(),'127.0.0.1',55581,10,1,1)
        with OwnedServer(spec,bindings={'python-fixture':Path(sys.executable)},output=journal.output,
                journal=journal,listener_owner=lambda *args:True,health_probe=lambda *args:True,
                availability_probe=lambda *args:None):time.sleep(15)
'''
        for mode in modes:
            with self.subTest(mode=mode):
                root = self.root/mode
                root.mkdir()
                owner = subprocess.Popen([sys.executable,'-I','-B','-S','-c',script,str(engine_root),
                    str(wrapper_root),str(root),mode],
                    creationflags=0x08000000,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
                try:
                    self.wait_file(root/'tree.json')
                    ids = json.loads((root/'tree.json').read_text())
                    process, child = self.hold(ids['pid']), self.hold(ids['grandchild'])
                    (root/'exit').touch()
                    self.assertEqual(owner.wait(timeout=5),23)
                    self.assertEqual(K.WaitForSingleObject(process,3000),0)
                    self.assertEqual(K.WaitForSingleObject(child,3000),0)
                finally:
                    if owner.poll() is None:
                        owner.kill()
                    owner.wait(timeout=5)

    def test_wrapper_failed_assignment_records_owned_start_without_running(self):
        from tether import _process
        job = WindowsJob()
        self.addCleanup(job.close)
        marker = self.root/'must-not-run'
        command=[sys.executable,'-I','-B','-S','-c',
                 'from pathlib import Path;import sys;Path(sys.argv[1]).touch()',str(marker)]
        primary = PermissionError('assignment fixture')
        with patch.object(_process,'process_tree_for',return_value=job), \
                patch.object(job,'_assign',side_effect=primary), \
                self.assertRaises(PermissionError) as caught:
            _process.supervise_command(command)
        self.assertIs(caught.exception,primary)
        report = primary.tether_engine_result.supervision
        self.assertTrue(report['process_started'])
        self.assertTrue(report['process_reaped'])
        self.assertEqual(report['termination_reason'],'supervisor_error')
        self.assertFalse(marker.exists())

    def test_job_shutdown_does_not_touch_other_owned_fixture_process(self):
        unrelated = subprocess.Popen([sys.executable,'-I','-B','-S','-c','import time;time.sleep(10)'],
            creationflags=0x08000000,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            job, process, child = self.tree()
            job.finish(time.monotonic()+3)
            process.wait(timeout=3)
            self.assertEqual(K.WaitForSingleObject(child,3000),0)
            self.assertIsNone(unrelated.poll())
        finally:
            unrelated.kill()  # This separate test-owned handle, never discovery by PID/port.
            unrelated.wait(timeout=5)

    def test_wrapper_interruption_after_resume_retains_start_without_retry(self):
        from tether import _process
        job = WindowsJob()
        self.addCleanup(job.close)
        original = job._resume_initial_thread
        primary = KeyboardInterrupt('interrupted after resume')
        def interrupted(deadline):
            original(deadline)
            raise primary
        with patch.object(_process,'process_tree_for',return_value=job), \
                patch.object(job,'_resume_initial_thread',side_effect=interrupted) as resumed, \
                self.assertRaises(_process.EngineInterrupted) as caught:
            _process.supervise_command([sys.executable,'-I','-B','-S','-c','import time;time.sleep(10)'])
        resumed.assert_called_once()
        self.assertIs(caught.exception.__cause__,primary)
        report = caught.exception.result.supervision
        self.assertTrue(report['process_started'])
        self.assertTrue(report['process_reaped'])
        self.assertEqual(report['termination_reason'],'interrupted')

if __name__=='__main__':unittest.main()
