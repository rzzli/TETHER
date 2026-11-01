"""Independent terminal report/code-pin review; no tests or provider reads."""
import ast
from collections import Counter
import hashlib,json,re,subprocess
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[3]
ASSETS=ROOT/'planning/review-assets/preprint-p09-20261101'
READY='e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def wire(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
def pin(path):
 raw=path.read_bytes();return dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(raw),bytes=len(raw))

def run():
 checks=[];issues=[]
 def need(name,condition):
  checks.append(dict(check=name,passed=bool(condition)))
  if not condition:issues.append(name)
 reports={};evidence={};gates={}
 source=(ROOT/'tools/validate.py').read_text(encoding='utf-8')
 tree=ast.parse(source)
 allowed=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='EXPECTED_CORE_SKIPS' for t in n.targets))
 for mode,stamp in [('core','224500'),('full','224000')]:
  path=ROOT/('data/cache/p09-'+mode+'-validation-v3-20261101T'+stamp+'Z.json');raw=path.read_bytes();report=json.loads(raw);reports[mode]=report
  log=ASSETS/(mode.upper()+'-VALIDATION-v3.txt');text=log.read_text(encoding='utf-8-sig')
  copied=ASSETS/(mode.upper()+'-VALIDATION-v3.json')
  need(mode+'_report_archive_copy_exact',copied.read_bytes()==raw)
  need(mode+'_terminal_1973_clean',report['status']=='passed' and report['mode']==mode and report['tests']['run']==1973 and report['tests']['errors']==report['tests']['failures']==0)
  skips=report['tests']['skipped'];reasons=Counter(s['reason'] for s in skips)
  need(mode+'_skip_scope',len({s['test'] for s in skips})==len(skips) and (len(skips)==94 and set(reasons)<=allowed if mode=='core' else not skips))
  need(mode+'_syntax_probes_package',report['powershell_syntax'] is True and report['required_probes_exit_code']==0 and report['packaging']['package_network_policy']=='offline' and report['packaging']['dependency_free_demo']=='passed'
       and report['packaging']['build_constraints_sha256']==sha((ROOT/'paper/release/build-constraints.txt').read_bytes()))
  summaries=re.findall(r'Ran ([0-9]+) tests in ([0-9.]+)s',text);outcomes=re.findall(r'^(?:OK[^\r\n]*|FAILED[^\r\n]*)$',text,re.M)
  need(mode+'_log_matches_terminal_report',summaries[-1][0]=='1973' and outcomes[-1]==('OK (skipped=94)' if mode=='core' else 'OK') and not re.search(r'^ERROR:',text,re.M))
  evidence[mode]=dict(report=pin(path),archived_report=pin(copied),log=pin(log))
  gates[mode]=dict(status='passed',collected=1973,executed=1973-len(skips),approved_skips=len(skips),skip_reasons=dict(reasons),failures=0,errors=0,unittest_seconds=float(summaries[-1][1]),complete_gate_seconds=report['elapsed_seconds'],powershell_syntax=True,required_probes_exit_code=0,packaging=report['packaging'],structural_scope_files=report['structural']['tracked_scope_files'])
 history=[]
 for mode in ('core','full'):
  for version in (1,2):
   path=ASSETS/(mode.upper()+'-VALIDATION-v'+str(version)+'.txt');text=path.read_text(encoding='utf-8-sig');summaries=re.findall(r'Ran ([0-9]+) tests in ([0-9.]+)s',text);outcomes=re.findall(r'^(?:OK[^\r\n]*|FAILED[^\r\n]*)$',text,re.M)
   need(mode+'_v'+str(version)+'_failure_preserved',bool(summaries) and outcomes[-1].startswith('FAILED'))
   history.append(dict(mode=mode,attempt=version,tests=int(summaries[-1][0]),seconds=float(summaries[-1][1]),outcome=outcomes[-1],evidence=pin(path)))
 head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 diff=subprocess.check_output(['git','diff','--name-only',head,'--','src/asof','tests','tools/validate.py','tools/review','tools/science','paper/release/code'],cwd=ROOT,text=True).strip()
 need('gate_source_commit_and_clean_code_tests',head=='3629337cda1e033228df67cb9c0046d6d9cc9049' and not diff)
 bundle=ROOT/'data/cache/p09-runtime-bundle-20261101T213500Z';protocol_raw=(bundle/'protocol.json').read_bytes();protocol=json.loads(protocol_raw)
 need('final_e284_READY',sha(protocol_raw)==READY and protocol['status']=='READY' and protocol['actual_reconstruction_authorized'] is True)
 actual={p.relative_to(bundle).as_posix() for p in bundle.rglob('*') if p.is_file()}
 need('pristine312_file_bundle',actual==set(protocol['files'])|{'protocol.json'} and len(actual)==312 and not any(n.endswith('.pyc') for n in actual))
 maps={};wheel_details={}
 for label,prefix,current in [('core','source/core/src/asof/',ROOT/'src/asof'),('replay','source/replay/src/asof_p05_replay/',ROOT/'paper/release/code/src/asof_p05_replay')]:
  current_map={p.relative_to(current).as_posix():sha(p.read_bytes()) for p in current.rglob('*') if p.is_file() and p.suffix in ('.py','.json')}
  frozen_map={n[len(prefix):]:d['sha256'] for n,d in protocol['files'].items() if n.startswith(prefix)}
  need(label+'_current_complete_payloads_match_frozen',current_map==frozen_map==protocol[label+'_files'] and len(current_map)==(92 if label=='core' else 8));maps[label]=current_map
 for name,d in protocol['files'].items():
  if d['role']=='reference_original_CC0':
   need('bundled_HGNC_size_only_not_reopened',(bundle/name).stat().st_size==d['bytes']==16973159)
  else:need('frozen_member_'+name,sha((bundle/name).read_bytes())==d['sha256'] and (bundle/name).stat().st_size==d['bytes'])
 for name,d in protocol['files'].items():
  if not name.endswith('.whl'):continue
  label='replay' if 'asof_p05_replay' in name else 'core';package='asof_p05_replay' if label=='replay' else 'asof'
  with zipfile.ZipFile(bundle/name) as z:
   payloads={n[len(package)+1:]:sha(z.read(n)) for n in z.namelist() if n.startswith(package+'/') and n.endswith(('.py','.json'))}
   need(label+'_frozen_wheel_payloads_match_current',payloads==maps[label])
   wheel_details[label]=dict(path=name,sha256=d['sha256'],package_payloads=len(payloads),members=len(z.namelist()))
 p05_path=ROOT/'planning/review-assets/preprint-p05-20261031/EXPERIMENT-READY-v1.json';p05=json.loads(p05_path.read_bytes())
 need('original_P06_READY_anchor',sha(p05_path.read_bytes())=='49c2ce672356bfcfd572a7b6c963c56bd5c96e3d042a9972f2c36434ebb8de3f')
 p05_pins={**p05['code_sha256'],**p05['extra_code_sha256']}
 need('all78_original_P05_code_pins_unchanged',len(p05_pins)==78 and all(sha((ROOT/name).read_bytes())==digest for name,digest in p05_pins.items()))
 suites={}
 for key,name,count in [('p05_separate','P05-COMPLETE-REGRESSIONS-v1.txt',199),('installed_fictional_no_bytecode','INSTALLED-NO-BYTECODE-TESTS-v2.txt',82),('release_preparation','ROOT-PREPARATION-AND-PACKAGE-TESTS-final-v3.txt',40)]:
  path=ASSETS/name;text=path.read_text(encoding='utf-8-sig');summaries=re.findall(r'Ran ([0-9]+) tests in ([0-9.]+)s',text);outcomes=re.findall(r'^(?:OK[^\r\n]*|FAILED[^\r\n]*)$',text,re.M)
  need(key+'_retained_PASS',summaries[-1][0]==str(count) and outcomes[-1]=='OK')
  suites[key]=dict(tests=count,seconds=float(summaries[-1][1]),log=pin(path))
 qualification_path=ROOT/'paper/release/qualification.json';qualification_raw=qualification_path.read_bytes();q=json.loads(qualification_raw)
 need('public_qualification_role_scope',q['status']=='PASS_LOCAL_WINDOWS_RESEARCH_ARTIFACT' and q['protocol_sha256']==READY and q['code_commit_for_framework_gates']==head and q['role']=='evaluation_only' and q['agent_visible'] is False and q['publication_authorized'] is False and q['owner_declarations']=='deferred' and q['scientific_validation']==q['study_independence']=='not_established')
 for mode in ('core','full'):
  projected=q['framework_gates'][mode];report=reports[mode];skips=report['tests']['skipped']
  need('public_'+mode+'_exact_projection',projected['report_sha256']==evidence[mode]['report']['sha256'] and projected['tests_collected']==report['tests']['run'] and projected['tests_executed']==report['tests']['run']-len(skips)
       and projected['approved_optional_skips']==len(skips) and projected['errors']==report['tests']['errors'] and projected['failures']==report['tests']['failures'] and projected['required_probes_exit_code']==0 and projected['packaging']==report['packaging'] and projected['elapsed_seconds']==report['elapsed_seconds'] and set(projected['skip_reasons'])=={s['reason'] for s in skips})
 for key,item in suites.items():
  need('public_suite_'+key,q['additional_test_suites'][key]['status']=='passed' and q['additional_test_suites'][key]['tests']==item['tests'] and q['additional_test_suites'][key]['log']=={k:item['log'][k] for k in ('sha256','bytes')})
 native=ROOT/'data/derived/preprint-p09-installed-20261101T205500Z/revision2/reconstruction-v2';audit=ROOT/'data/derived/preprint-p09-installed-20261101T205500Z/revision2/audit-v2'
 need('public_native_report_receipt_pins',q['native_reconstruction']['report_sha256']==sha((native/'reconstruction.json').read_bytes()) and q['native_reconstruction']['receipt_sha256']==sha((native/'receipt.json').read_bytes()))
 need('public_audit_report_receipt_pins',q['separate_source_audit']['report_sha256']==sha((audit/'audit.json').read_bytes()) and q['separate_source_audit']['receipt_sha256']==sha((audit/'receipt.json').read_bytes()) and q['separate_source_audit']['checks']==6862)
 peer=ASSETS/'ACTUAL-QUALIFICATION-PEER-REVIEW-v2.json'
 need('public3481_peer_binding',q['sealed_metadata_peer_review']['sha256']==sha(peer.read_bytes()) and q['sealed_metadata_peer_review']['bytes']==peer.stat().st_size and q['sealed_metadata_peer_review']['checks']==3481 and q['sealed_metadata_peer_review']['provider_sources_reopened'] is False)
 need('public_unknowns_and_no_new_calls',q['unsupported_or_unmeasured']==dict(current_hosted_ci='not_executed',fresh_external_reacquisition='untested',native_linux_replay='not_qualified',public_deposit=None,total_physical_io_bytes=None,total_platform_cost_usd=None) and all(type(q[k]) is int and q[k]==0 for k in ('new_model_calls','new_provider_downloads','provider_spending_usd')))
 need('public_projection_no_private_roots_or_fact_values',not re.search(r'(?i)(?:[A-Z]:[\\/]Users[\\/]|[A-Z]:[\\/]Projects|/Users/|/home/|zzric|drug_target_agents_data)',qualification_raw.decode().replace('\\\\','\\')) and not re.search(r'"(?:facts|raw_output|source_records|expected_values)"\s*:',qualification_raw.decode()))
 need('preparation_failure_limitation_retained',(ASSETS/'PREPARATION-TEMP-FAILURE-final-v1.md').exists())
 return dict(schema='p09.final_gate_peer_review.v1',status='PASS_FINAL_LOCAL_GATES_AND_PREZIP_QUALIFICATION_METADATA' if not issues else 'FAIL_FINAL_GATE_REVIEW',source_commit=head,checks=checks,check_count=len(checks),unresolved_findings=issues,gate_evidence=evidence,gates=gates,prior_failed_attempts=history,separate_suites=suites,qualified_protocol_sha256=READY,qualified_bundle_members=312,current_package_payloads=100,package_map_sha256=sha(wire(maps)),original_P05_code_pins=78,P05_READY=pin(p05_path),frozen_wheels=wheel_details,public_qualification=pin(qualification_path),preparation_failure_note=pin(ASSETS/'PREPARATION-TEMP-FAILURE-final-v1.md'),limits=['This reviews terminal evidence, not a rerun; package-gate temporary wheel bodies are not reopened, and their reported whole-wheel hashes need not equal each other or the frozen wheel. Frozen package payload bytes were checked independently.','Structural file counts7280/7282 cover different workspace snapshots; runtime/tests/helper code is clean at the common3629337commit. No blanket326historical-file immutability claim.','Counts overlap across configurations and suites; they are not additive independent samples.','Only bundled HGNC size was checked here; its provider body was not reopened. Prior frozen/source audits retain its exact hash qualification.','Current hosted CI/native Linux/fresh external reacquisition/scientific validity/independence remain unqualified.','This is preZIP qualification-input review; final archive closure/readback/privacy/rights review and P10/owner declarations are separate.'],broad_tests_rerun=False,protected_or_human_data_read=False,provider_originals_reopened=False)

if __name__=='__main__':
 report=run();path=ASSETS/'FINAL-GATE-PEER-REVIEW-v1.json'
 with path.open('xb') as stream:stream.write(json.dumps(report,indent=2).encode()+b'\n')
 print(json.dumps({k:report[k] for k in ('status','check_count','unresolved_findings','gates')},indent=2))
