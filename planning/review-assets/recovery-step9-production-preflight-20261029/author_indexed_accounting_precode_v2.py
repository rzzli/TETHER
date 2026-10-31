"""Two finite harness coverage closures; retain all first source/proof bytes."""
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def put(name,raw):
 path=HERE/name
 with path.open('xb') as out:out.write(raw)
 return pin(path)
def publish(name,value):return put(name,(json.dumps(value,sort_keys=True,indent=2)+'\n').encode('utf-8'))
def main():
 before=HERE/'indexed_accounting_controls_v1.py';assert pin(before)['sha256']=='bd7ea044253609c74396190658ddaadedd4d1bcc997e81391db7ded079e0d86e'
 text=before.read_text(encoding='utf-8')
 old="    self.assertEqual(measured['iterated_items'],0);self.assertEqual(measured['membership_items'],0)\n    self.assertLessEqual(measured['direct_index_items'],16)"
 new=old+"\n    self.assertEqual(measured['slice_copied_items'],0);self.assertLessEqual(measured['len_calls'],32)"
 assert text.count(old)==1;text=text.replace(old,new)
 old="   test.assertIs(w.owner._accounting_fault,error)\n   # Reporting is not a cache repair or a fresh eligibility stamp."
 new="""   test.assertIs(w.owner._accounting_fault,error)
   # Otherwise-valid work check isolates quarantine (already-open acquire cannot).
   # Same clock100 is before original work395/hard400; no changed deadline.
   test.assertEqual((w.clock.value,w.owner.origin.now,w.owner.origin.work_end,w.owner.origin.hard_end),(100,100,395,400))
   binding_before=len(w.binding.records);sink_before=len(w.sink.records)
   for _ in range(2):
    with test.assertRaises(BaseException):D.invoke(w.owner.check)
    test.assertIs(w.owner.primary,error);test.assertIs(w.owner._accounting_fault,error)
   test.assertEqual((len(w.binding.records),len(w.sink.records)),(binding_before,sink_before),'quarantine check dispatched')
   guard_report=snapshot(w,calls,name+'_after_quarantine_check')
   for key in ('origin','calls','api_counters','byte_totals','journal','outputs','stages','gates','early_context','evidence_context'):
    test.assertEqual(guard_report[key],first[key],'quarantine advanced '+key)
   observations.append(dict(name=name+'_otherwise_valid_work_check',window='post_canonical_report',refused=True,clock=100,binding_dispatches=0,sink_callbacks=0,source_facts_and_progress_unchanged=True,original_primary_preserved=True))
   # Reporting is not a cache repair or a fresh eligibility stamp."""
 assert text.count(old)==1;text=text.replace(old,new)
 old="  before=len(w.binding.records)\n  with test.assertRaises(BaseException):D.invoke(w.view.acquire,w.specs[1])\n  test.assertEqual(len(w.binding.records),before,'fresh work reached binding after fault')"
 new="  # In CTRL5 this file was already opened: only an additional existing guard,\n  # not evidence that accounting quarantine is effective. The check above is.\n"+old.replace('fresh work reached binding after fault','additional acquire guard dispatched')
 assert text.count(old)==1;text=text.replace(old,new)
 ast.parse(text)
 source=put('indexed_accounting_controls_v2.py',text.encode('utf-8'))
 old_protocol=json.loads((HERE/'INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v1.json').read_bytes())
 protocol=dict(old_protocol,schema_version=2,recorded_at_utc=datetime.now(timezone.utc).isoformat(),status='FROZEN_PRE_CODE_SIX_CONTROLS_TWO_COVERAGE_CLOSURES',test_source=source,preserved_v1={n:pin(HERE/n) for n in ('indexed_accounting_controls_v1.py','INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v1.json','INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v1.json','INDEXED-ACCOUNTING-ACTUAL-V2-BEFORE-PROOF-v1.json')})
 protocol['v2_exact_harness_delta']=[
  'CTRL3 includes zero slice_copied_items and len_calls<=32 in addition to the unchanged iteration/membership/index assertions.',
  'Indexed CTRL5/6 require otherwise-valid owner.check() clock100 before original work395/hard400 to refuse after canonical reports with same original fault and no binding/sink callback. Existing acquire guard explicitly not an isolated quarantine proof when file already open.',
  'No fixture/source/API/cap/control-family/expected raw-fact change; baseline still uses real V2 append/store boundaries. All original failed-baseline results retained.'
 ]
 protocol['controls'][4]['quarantine_isolation']='Indexed mode: actual owner.check() while healthy clock100 would allow work; requires rejection after accounting failure without API/sink callback. Already-open acquire is additional guard only.'
 p=publish('INDEXED-ACCOUNTING-PRECODE-TEST-CONTRACT-v2.json',protocol)
 delta=publish('INDEXED-ACCOUNTING-PRECODE-CONTROL-DELTA-v2.json',dict(schema_version=2,status='TWO_HARNESS_COVERAGE_CLOSURES_ONLY_NOT_SUBJECT_BUGS',before=pin(before),after=source,contract=p,changes=protocol['v2_exact_harness_delta'],unchanged=['six control families','V2 three source bytes','209B cohort/frozen48/publicDATA/caps','six original method names','all baseline raw facts and expected four hot failures'],author=pin(Path(__file__).resolve()),subject_runs_before_v2_freeze=0,implementation_authorized=False))
 for name in ('shared_owner_v3.py','shared_file_ports_v3.py','continue_verification_v3.py'):
  assert not (HERE/name).exists() and not (HERE.parent/'recovery-step9-shared-owner-20261029'/name).exists()
 f=publish('INDEXED-ACCOUNTING-PRECODE-CONTROL-FREEZE-v2.json',dict(schema_version=2,status='FROZEN_TESTS_BEFORE_V3_IMPLEMENTATION_AND_BEFORE_V2_CLOSURE_REPLAY',recorded_at_utc=datetime.now(timezone.utc).isoformat(),protocol=p,test_source=source,delta=delta,author=pin(Path(__file__).resolve()),preserved_v1=protocol['preserved_v1'],subject_runs_before_this_freeze=0,prospective_source_present=False,implementation_authorized=False,actual_target_API_calls=0,original_payload_operations=0,all_real_qualification_flags_false=True))
 print(json.dumps(dict(source=source,protocol=p,delta=delta,freeze=f)))
if __name__=='__main__':main()
