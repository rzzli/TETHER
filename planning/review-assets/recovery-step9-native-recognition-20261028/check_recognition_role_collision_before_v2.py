"""Regression-first pure collision cases against preserved v1; no payload/API access."""
import hashlib
from importlib import util
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
SOURCE=HERE/'recognition_runtime_roles_v1.py'
REPORT=HERE/'RECOGNITION-ROLE-COLLISION-REGRESSION-BEFORE-v2.json'
CONTRACT=HERE/'RECOGNITION-EXECUTION-CONTRACT-v1.json'
MANIFEST=HERE/'RECOGNITION-EXPECTED-PACK-METADATA-v1.json'
contract=json.loads(CONTRACT.read_text(encoding='utf-8'));manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
spec=util.spec_from_file_location('preserved_roles_before_collision_fix',SOURCE)
h=util.module_from_spec(spec);spec.loader.exec_module(h)
CPU,SHARDS,PACK=contract['CPU_descriptor'],contract['ordered_shard_descriptors'],manifest['pack']
OBSERVED=[]
class Checks(unittest.TestCase):
    def test_CPU_case_alias_cannot_enter_software_role(self):
        row=dict(CPU,path=CPU['path'].swapcase())
        with self.assertRaises(RuntimeError):OBSERVED.append(h.validate_record(row,software_records=[row],CPU=CPU,shards=SHARDS,pack=PACK))
    def test_CPU_slash_alias_cannot_enter_software_role(self):
        row=dict(CPU,path=CPU['path'].replace('\\','/'))
        with self.assertRaises(RuntimeError):OBSERVED.append(h.validate_record(row,software_records=[row],CPU=CPU,shards=SHARDS,pack=PACK))
    def test_case_aliases_cannot_duplicate_software_identity(self):
        row=dict(path=r'D:\qualified\software.txt',bytes=1,sha256='0'*64);alias=dict(row,path=row['path'].swapcase())
        with self.assertRaises(RuntimeError):OBSERVED.append(h.validate_record(row,software_records=[row,alias],CPU=CPU,shards=SHARDS,pack=PACK))
    def test_noncanonical_dot_spelling_cannot_enter_software_role(self):
        row=dict(path=r'D:\qualified\.\software.txt',bytes=1,sha256='0'*64)
        with self.assertRaises(RuntimeError):OBSERVED.append(h.validate_record(row,software_records=[row],CPU=CPU,shards=SHARDS,pack=PACK))

def pin(path):
    raw=Path(path).read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
if __name__=='__main__':
    assert not REPORT.exists()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    value=dict(schema_version=1,status='failed_expected_before_canonical_role_fix' if not result.wasSuccessful() else 'unexpected_pass',
        tests=result.testsRun,failures=[str(c) for c,_ in result.failures],errors=[str(c) for c,_ in result.errors],
        source=pin(SOURCE),checker=pin(Path(__file__)),contract=pin(CONTRACT),expected_pack_manifest=pin(MANIFEST),observed_admissions=OBSERVED,
        activity=dict(CPU_reads=0,GGUF_reads=0,SDK_constructors=0,children=0),scope='Generic pure role-key defect; no future exact-roster runtime bypass asserted')
    with REPORT.open('x',encoding='utf-8') as out:json.dump(value,out,sort_keys=True,indent=2);out.write('\n')
    print(json.dumps(dict(proof=pin(REPORT))))
    raise SystemExit(0 if result.wasSuccessful() else 1)
