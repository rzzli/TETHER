"""Independent literal/data checks only; never executes helper bytecode."""
import ast
import hashlib
import json
from pathlib import Path
import unittest

HERE=Path(__file__).resolve().parent
FIXTURE=HERE/'SHARED-OWNER-SYNTHETIC-INPUT-COHORT-v1.json'
EXPECTED_SHA='eb5147d200bcc0108b71968d69f6b251c29b56dd52d926a8606504682134d9b8'
RAW=FIXTURE.read_bytes()
assert hashlib.sha256(RAW).hexdigest()==EXPECTED_SHA
DATA=json.loads(RAW)
EXPECTED_BYTES={
 'cohort_leaf':b'MARKER = "cohort-leaf-v1"\ndef marker():\n    return MARKER\n',
 'cohort_entry':b'from cohort_leaf import marker\ndef run():\n    return ("cohort-entry-v1", marker())\n',
 'metadata':b'{"schema":"synthetic-cohort-v1","marker":"metadata-only","value":7}\n',
}

def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

class LiteralChecks(unittest.TestCase):
 def test_explicit_bytes_sizes_and_sha(self):
  self.assertEqual([b['id'] for b in DATA['blobs']],['cohort_leaf','cohort_entry','metadata'])
  for blob in DATA['blobs']:
   with self.subTest(blob=blob['id']):
    raw=bytes.fromhex(blob['utf8_hex'])
    self.assertEqual(raw,EXPECTED_BYTES[blob['id']])
    self.assertEqual(len(raw),blob['bytes'])
    self.assertEqual(hashlib.sha256(raw).hexdigest(),blob['sha256'])
    self.assertEqual(raw.decode('utf-8').encode('utf-8'),raw)

 def test_exact_fictitious_roles_and_paths(self):
  self.assertEqual(DATA['path_namespace'],'D:\\FictionalSharedOwnerCohort')
  for blob in DATA['blobs']:
   self.assertIs(blob['capture'],True)
   self.assertEqual(blob['path'],DATA['path_namespace']+'\\'+blob['id']+('.json' if blob['id']=='metadata' else '.py'))
   self.assertEqual(blob['role'],'owner_metadata' if blob['id']=='metadata' else 'software')
   self.assertEqual(blob['phase'],'remaining_captured_input' if blob['id']=='metadata' else 'early_source')
  self.assertEqual(len({b['path'].lower() for b in DATA['blobs']}),3)

 def test_closed_toy_source_dependency_graph_without_execution(self):
  modules=DATA['closed_modules']
  self.assertEqual(modules,[dict(fullname='cohort_leaf',blob_id='cohort_leaf',dependencies=[],package=False),dict(fullname='cohort_entry',blob_id='cohort_entry',dependencies=['cohort_leaf'],package=False)])
  self.assertEqual(DATA['stdlib_dependencies'],[])
  leaf=ast.parse(EXPECTED_BYTES['cohort_leaf'])
  entry=ast.parse(EXPECTED_BYTES['cohort_entry'])
  self.assertFalse(any(isinstance(n,(ast.Import,ast.ImportFrom)) for n in ast.walk(leaf)))
  imports=[n for n in ast.walk(entry) if isinstance(n,(ast.Import,ast.ImportFrom))]
  self.assertEqual(len(imports),1)
  self.assertIsInstance(imports[0],ast.ImportFrom)
  self.assertEqual((imports[0].module,imports[0].level),('cohort_leaf',0))
  self.assertEqual([(x.name,x.asname) for x in imports[0].names],[('marker',None)])
  self.assertEqual([(n.name,len(n.args.args)) for n in leaf.body if isinstance(n,ast.FunctionDef)],[('marker',0)])
  self.assertEqual([(n.name,len(n.args.args)) for n in entry.body if isinstance(n,ast.FunctionDef)],[('run',0)])
  calls=[n for n in ast.walk(entry) if isinstance(n,ast.Call)]
  self.assertEqual(len(calls),1);self.assertIsInstance(calls[0].func,ast.Name);self.assertEqual(calls[0].func.id,'marker')
  self.assertEqual(json.loads(EXPECTED_BYTES['metadata']),DATA['expected_toy_values']['metadata_object'])

 def test_input_history_expectations_and_nonclaims(self):
  expected_sizes={'cohort_leaf':58,'cohort_entry':83,'metadata':68}
  for row in DATA['successful_lifecycle_input_history']:
   self.assertEqual(row,dict(blob_id=row['blob_id'],original_acquisition_histories=1,whole_blob_hash_histories=1,capture_histories=1,continuation_reopens=0,continuation_rehashes=0,known_read_bytes=expected_sizes[row['blob_id']],hashed_bytes=expected_sizes[row['blob_id']],captured_bytes=expected_sizes[row['blob_id']]))
  self.assertEqual(DATA['totals'],dict(early_sources=2,remaining_captured_inputs=1,total_blobs=3,early_bytes=141,remaining_bytes=68,total_bytes=209))
  for field in ('fixture_behavior_qualified','original_sources_authenticated','FFI_registration_proven','production_owner_bound','profile_qualified','runtime_authorized'):
   self.assertIs(DATA[field],False)
  self.assertEqual(DATA['actual_API_calls'],0)

if __name__=='__main__':
 report_path=HERE/'SHARED-OWNER-SYNTHETIC-INPUT-PREPARATION-PROOF-v1.json'
 freeze_path=HERE/'SHARED-OWNER-SYNTHETIC-INPUT-FREEZE-v1.json'
 assert not report_path.exists() and not freeze_path.exists()
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LiteralChecks))
 report=dict(schema_version=1,status='passed' if result.wasSuccessful() else 'failed',methods=result.testsRun,failures=[dict(test=str(t),detail=d) for t,d in result.failures],errors=[dict(test=str(t),detail=d) for t,d in result.errors],fixture=pin(FIXTURE),author=pin(HERE/'author_shared_owner_input_cohort_v1.py'),checker=pin(Path(__file__).resolve()),blobs=3,total_bytes=209,helper_sources_executed=False,under_test_components_imported=False,embedded_paths_opened=False,actual_API_calls=0,FFI_registration_proven=False,production_owner_bound=False,profile_qualified=False,runtime_authorized=False,scope='Literal bytes/SHA/role/closed-source-AST and once-history framing checks only. No loader/compile/fixture behavior/source-original qualification.')
 with report_path.open('xb') as out:out.write((json.dumps(report,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 if result.wasSuccessful():
  freeze=dict(schema_version=1,status='SMALL_SYNTHETIC_INPUT_COHORT_FROZEN_FOR_FUTURE_INTERFACE_FIXTURES',fixture=report['fixture'],author=report['author'],checker=report['checker'],preparation_proof=pin(report_path),scope=report['scope'],actual_API_calls=0,fixture_behavior_qualified=False,runtime_authorized=False)
  with freeze_path.open('xb') as out:out.write((json.dumps(freeze,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(dict(proof=pin(report_path),status=report['status'],freeze=pin(freeze_path) if freeze_path.exists() else None)))
 raise SystemExit(0 if result.wasSuccessful() else 1)
