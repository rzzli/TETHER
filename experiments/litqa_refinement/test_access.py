"""Real audit-hook controls for coordinator/actor separation."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class RoleAccessTests(unittest.TestCase):
    def test_loopback_encoding_has_no_lazy_empty_cache_denials(self):
        root=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);cache=base/'empty-import-cache';cache.mkdir()
            script=r'''
import sys
from pathlib import Path
sys.path[:0]=[sys.argv[1],str(Path(sys.argv[1])/'src'),str(Path(sys.argv[1])/'packages/tether/src')]
from experiments.litqa_refinement.access import RoleAudit
output=Path(sys.argv[2])/'worker';output.mkdir()
guard=RoleAudit(inputs=[],code_files=[],runtime_roots=[sys.prefix,sys.base_prefix],model_files=[],output=output)
guard.activate()
assert '127.0.0.1'.encode('idna')==b'127.0.0.1'
guard.flush()
assert guard.denials==0, guard.denials
'''
            result=subprocess.run([sys.executable,'-I','-B','-X','pycache_prefix='+str(cache),'-c',script,str(root),str(base)],
                capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertFalse(any(cache.rglob('*.pyc')))

    def test_actor_cannot_read_baseline_other_member_or_evaluator_files(self):
        root=Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            script=r'''
import json,sys
from pathlib import Path
sys.path[:0]=[sys.argv[1],str(Path(sys.argv[1])/'src'),str(Path(sys.argv[1])/'packages/tether/src')]
from experiments.litqa_refinement.access import RoleAudit
base=Path(sys.argv[2]);output=base/'worker';output.mkdir()
visible=base/'baseline.json';visible.write_text('original')
secret=base/'keys.json';secret.write_text('keys')
sibling=output/'repair';sibling.mkdir();(sibling/'result.json').write_text('previous answer')
guard=RoleAudit(inputs=[visible],code_files=[],runtime_roots=[],model_files=[],output=output)
guard.activate()
assert visible.read_text()=='original'
denied=[]
with guard.actor('removal',output/'removal'):
    for file in (visible,secret,sibling/'result.json'):
        try:file.read_bytes()
        except PermissionError:denied.append(file.name)
    own=output/'removal';own.mkdir();(own/'INPUT.json').write_text('empty source projection')
    assert (own/'INPUT.json').read_text()=='empty source projection'
assert visible.read_text()=='original'
try:secret.read_bytes()
except PermissionError:denied.append('coordinator-key-denied')
guard.flush();assert guard.denials==4 and len(denied)==4
print(json.dumps(dict(denied=denied,role=guard.role)))
'''
            result=subprocess.run([sys.executable,'-I','-B','-c',script,str(root),str(path)],capture_output=True,text=True,timeout=20)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['role'],'coordinator')
            events=[json.loads(line) for line in (path/'worker/io-audit.jsonl').read_text().splitlines()]
            self.assertEqual(sum(row.get('allowed') is False for row in events),4)
            self.assertTrue(all(row['role']=='removal' for row in events if row.get('path','').endswith('INPUT.json')))


if __name__=='__main__':unittest.main()
