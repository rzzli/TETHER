"""Read retained NEW proof metadata; freeze exact source/pure evidence only."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PRECODE=HERE.parent/'recovery-step9-production-preflight-20261029'
def pin(path):
 raw=path.read_bytes();return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def load(name,digest):
 path=HERE/name;assert pin(path)['sha256']==digest;return json.loads(path.read_bytes())
def main():
 proof=load('INDEXED-ACCOUNTING-INDEPENDENT-ACTUAL-PROOF-v3.json','173bfdeba4a25bab32ac676c1af194805cd33dc847b2616e12f4ffa7a905d660')
 author=load('INDEXED-ACCOUNTING-AUTHOR-CONTROLS-PURE-PROOF-v3.json','80d93cc5a7d5f53229380b79c8d65d02d70130fa563a33acbaee0aaa900c9b91')
 supplement=load('INDEXED-ACCOUNTING-AUTHOR-SUPPLEMENT-PURE-PROOF-v3.json','a86d0da9642ef79a0432e50cea7a3f4d203824a29c3f367746daca06549bbe81')
 assert proof['status']=='passed' and proof['methods']==15 and not proof['failures'] and not proof['errors']
 assert (proof['histories_executed'],proof['histories_matched'],proof['snapshot_count'])==(48,48,372)
 assert not proof['audit_denials'] and all(proof['source_unchanged'].values()) and all(proof['test_unchanged'].values())
 assert not any(proof['qualification'].values())
 for control,expected in ((author,12),(supplement,4)):
  assert control['status']=='PASS' and control['methods']==expected and len(control['results'])==expected and all(r['passed'] is True for r in control['results'])
  for item in control['source_pins']:assert item['sha256']==proof['source_pins'][Path(item['name']).stem]['sha256']
 assert pin(HERE/'check_shared_owner_author_controls_v3.py')['sha256']==author['checker_sha256']
 assert pin(HERE/'check_shared_owner_author_supplement_v3.py')['sha256']==supplement['checker_sha256']
 pins={n:v for group in ('source_pins','test_pins','dependencies') for n,v in proof[group].items()}
 for name,v in pins.items():assert pin(Path(v['path']))==v,name
 for name in ('INDEXED-ACCOUNTING-INDEPENDENT-ACTUAL-PROOF-v3.json','INDEXED-ACCOUNTING-AUTHOR-CONTROLS-PURE-PROOF-v3.json','INDEXED-ACCOUNTING-AUTHOR-SUPPLEMENT-PURE-PROOF-v3.json','INDEXED-ACCOUNTING-INDEPENDENT-SOURCE-BINDING-v3.json','INDEXED-ACCOUNTING-INDEPENDENT-RUN-FREEZE-v3.json','run_indexed_accounting_actual_v3_v1.py','author_indexed_accounting_source_binding_v3.py','check_shared_owner_author_controls_v3.py','check_shared_owner_author_supplement_v3.py'):
  pins[name]=pin(HERE/name)
 hot=[o for o in proof['indexed_six_control_observations'] if o['window']=='clean_hot']
 assert len(hot)==4
 for o in hot:
  assert all(o['metrics'][key]==0 for key in ('iterated_items','membership_items','slice_copied_items'))
  assert o['metrics']['direct_index_items']<=16 and o['metrics']['len_calls']<=32
 cold=[o for o in proof['indexed_six_control_observations'] if o['window']=='canonical_report_allowed']
 assert cold and all(o['metrics']['iterated_items']==o['calls'] for o in cold)
 quarantine=[o for o in proof['indexed_six_control_observations'] if o['window']=='post_canonical_report']
 assert len(quarantine)==5 and all(o['refused'] and o['binding_dispatches']==o['sink_callbacks']==0 and o['source_facts_and_progress_unchanged'] for o in quarantine)
 output=dict(schema_version=3,status='EXACT_INDEXED_N4_SOURCE_PURE_EVIDENCE_FROZEN_INDEPENDENT_SOURCE_PEER_PENDING',recorded_at_utc=datetime.now(timezone.utc).isoformat(),inputs=pins,freezer=pin(Path(__file__).resolve()),independent_methods=15,unchanged_histories=48,histories_matched=48,same_five_family_regression_methods=8,precode_indexed_control_methods=6,author_methods_separate=12,author_supplement_methods_separate=4,strict_full48_snapshots=372,actual_full48_fake_dispatches=518,actual_full48_in_memory_toy_module_execs=34,actual_hot_metrics=hot,explicit_canonical_report_metrics=cold,quarantine_checks=quarantine,source_and_test_bytes_unchanged=True,audit_denials=[],qualification=proof['qualification'],chronology=[
  'Accepted V2, frozen48 oracle, SAME8 regressions and strict validator predate indexed implementation.',
  'Pre-code six controls d76/protocolcccf/freeze52da and actual accepted-V2 BEFORE24da predate V3 code. Prior control-v1/HOLD/baseline88dd preserved.',
  'Source pause8c010 freezes all3 before any V3 subject import/test. OS author16 and independent15 then execute separately on those same immutable bytes.',
  'Source-binding55910/run-freeze6855 source_tests_before_this_* = 0 are LOCAL independent-run counts; they do not assert OS author controls had not run. No zero-historical-subject-execution claim.',
  'This evidence-freeze performs only bounded NEW metadata/proof/pin checks, no subject replay or additional native/compiler/original operation.'
 ],limits=[
  'Hot metrics are deterministic source algorithm evidence for fixed valid N3 worlds under current N4 caps, not timing, production size fit or full-roster capacity.',
  'Static source peer must rule out direct base-list/dict-values bypass or hidden report called from read work; observed metrics alone cannot establish that.',
  'Reporting windows are explicit; all retained sampled canonical reports visit r records once. No cache healing, cleared fault or renewed owner/clock/registry follows.',
  'No real entry/FFI/Win32/physical sink/source closure/old source/model/native/profile/scientific qualification. All current real flags stay false; app/defaults unchanged.'
 ],actual_target_API_calls=0,original_payload_or_sourceclosure_operations=0,component_accepted=False)
 path=HERE/'INDEXED-ACCOUNTING-ACTUAL-EVIDENCE-FREEZE-v3.json'
 with path.open('xb') as out:out.write((json.dumps(output,sort_keys=True,indent=2)+'\n').encode('utf-8'))
 print(json.dumps(dict(freeze=pin(path),independent_methods=15,histories=48,author_methods=16,hot_controls=4,cold_reports=len(cold),quarantine_checks=len(quarantine))))
if __name__=='__main__':main()
