"""Independent read-only archive closure; provider archive content is hash-only."""
from collections import Counter
from datetime import datetime
import hashlib,io,json,re,stat,zipfile
from pathlib import Path,PurePosixPath

ROOT=Path(__file__).resolve().parents[3]
ASSETS=ROOT/'planning/review-assets/preprint-p09-20261101'
ZIP=ROOT/'data/derived/preprint-p09-release-20261101T232900Z/asof-research-artifact-0.1.0.zip'
PIN='f4d7ab4bb1a0b79c0ecadbac15891f4cc2925abe624298e8a48a762190b6782e'
READY='e28461a5681bcaaae89752f0cf7e1ac6fb644c4eebdf501a1f2c2ec7c26dd529'
MANIFEST='30f9cca157eff20d250d89dbc91497290936e27d64fb5038754a813a6fc4c40e'

def sha(raw):return hashlib.sha256(raw).hexdigest()
def wire(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()

def run():
 checks=[];issues=[];privacy=[]
 def need(name,v):
  checks.append(dict(check=name,passed=bool(v)))
  if not v:issues.append(name)
 raw=ZIP.read_bytes();repeat=ZIP.with_name('asof-research-artifact-0.1.0-repeat.zip').read_bytes()
 need('external_archive_byte_anchor',sha(raw)==PIN and len(raw)==20712230)
 need('fresh_repeat_exact_bytes',raw==repeat)
 record_path=ROOT/'paper/release/RELEASE-RECORD.json';record_raw=record_path.read_bytes();record=json.loads(record_raw)
 need('external_release_record_matches',record['archive']['sha256']==PIN and record['archive']['bytes']==len(raw) and record['archive']['members']==315
      and record['archive']['fresh_second_build_bytes_equal'] is True and record['release_manifest_sha256']==MANIFEST and record['reconstruction_protocol_sha256']==READY)
 need('record_scope',record['status']=='PACKAGED_AND_READBACK_VERIFIED' and record['role']=='evaluation_only' and record['agent_visible'] is False and record['publication_authorized'] is False and record['owner_declarations']=='deferred')
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  names=z.namelist();need('unique_sorted315_members',len(names)==len(set(names))==315 and names==sorted(names) and not z.comment)
  manifest_raw=z.read('RELEASE-MANIFEST.json');manifest=json.loads(manifest_raw)
  protocol_raw=z.read('artifact/protocol.json');protocol=json.loads(protocol_raw)
  qraw=z.read('qualification.json');q=json.loads(qraw)
  need('manifest_exact_external_pin',sha(manifest_raw)==MANIFEST)
  need('qualified_protocol_exact_pin',sha(protocol_raw)==READY and protocol_raw==(ROOT/'data/cache/p09-runtime-bundle-20261101T213500Z/protocol.json').read_bytes())
  expected={'artifact/'+name for name in protocol['files']}|{'artifact/protocol.json','README.md','qualification.json','RELEASE-MANIFEST.json'}
  need('exact_positive_allowlist_closure',set(names)==expected)
  need('manifest_complete_self_excluded',set(manifest['files'])==set(names)-{'RELEASE-MANIFEST.json'})
  need('manifest_role_and_authority',manifest['protocol_sha256']==READY and manifest['public_qualification_sha256']==sha(qraw) and manifest['role']=='evaluation_only' and manifest['agent_visible'] is False and manifest['publication_authorized'] is False and manifest['scientific_validation']=='not_established')
  need('public_qualification_exact_current_bytes',qraw==(ROOT/'paper/release/qualification.json').read_bytes() and sha(qraw)==record['public_qualification_sha256'])
  need('outer_README_exact_current_bytes',z.read('README.md')==(ROOT/'paper/release/PACKAGE-README.md').read_bytes())
  frozen=datetime.fromisoformat(protocol['frozen_at_utc'].replace('Z','+00:00'));stamp=(frozen.year,frozen.month,frozen.day,frozen.hour,frozen.minute,frozen.second//2*2)
  for info in z.infolist():
   name=info.filename;p=PurePosixPath(name)
   need('safe_member_'+name,not p.is_absolute() and '..' not in p.parts and ':' not in name and '\\' not in name and not info.is_dir() and stat.S_IFMT(info.external_attr>>16)!=stat.S_IFLNK)
   need('deterministic_metadata_'+name,info.compress_type==zipfile.ZIP_STORED and info.date_time==stamp and not info.comment and not info.extra)
   need('forbidden_asset_class_'+name,not name.endswith(('.pyc','.parquet','.gguf','.safetensors','.ttf','.otf','.woff','.exe')) and not re.search(r'(?i)(?:^|/)(?:\.env|credentials|human[_-]responses?|clinical[_-]outcomes?|gold_evidence)(?:/|$)',name))
   if name=='RELEASE-MANIFEST.json':continue
   payload=z.read(name);anchor=manifest['files'][name]
   need('member_hash_size_role_'+name,len(payload)==anchor['bytes'] and sha(payload)==anchor['sha256'] and type(anchor['role']) is str and bool(anchor['role']))
   if name.startswith('artifact/'):
    logical=name.removeprefix('artifact/')
    if logical!='protocol.json':need('frozen_descriptor_'+logical,anchor=={k:protocol['files'][logical][k] for k in ('sha256','bytes','role')})
  roles=Counter(d['role'] for d in manifest['files'].values())
  need('evaluation_comparison_roles',manifest['files']['qualification.json']['role']=='evaluation_only' and manifest['files']['artifact/evaluation/comparison.json']['role']=='evaluation_only')
  originals={n for n in names if n.startswith('artifact/included-originals/')}
  hgnc='artifact/included-originals/reference/hgnc_symbols/snapshot_2026-10-10/hgnc_complete_set.txt'
  need('exact_original_payload_exception',len(originals)==138 and sum(n.endswith('.json') for n in originals)==137 and hgnc in originals
       and sha(z.read(hgnc))=='64fcdfcdf9bc0853ec502e0e4c7d6eb12647b2ca8b0e635ea04bdb584856baf7' and z.getinfo(hgnc).file_size==16973159)
  cards={n for n in names if n.startswith('artifact/cards/')};need('six_rights_cards_present',len(cards)==6)
  need('HGNC_CC0_exception_documented',b'CC0' in z.read('artifact/cards/HGNC-EXACT-REPLAY-ADDENDUM-v1.md') and b'136' in z.read('artifact/cards/OPEN-TARGETS-25.09-DATA-CARD-DRAFT-v1.md'))
  for n in ('artifact/source/core/LICENSE','artifact/source/replay/LICENSE','artifact/source/presentation/LICENSE'):
   need('Apache_license_'+n,sha(z.read(n))=='cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30')
  for name in [n for n in names if n.endswith('.whl')]:
   label='replay' if 'asof_p05_replay' in name else 'core';package='asof_p05_replay' if label=='replay' else 'asof'
   with zipfile.ZipFile(io.BytesIO(z.read(name))) as wheel:
    payloads={n[len(package)+1:]:sha(wheel.read(n)) for n in wheel.namelist() if n.startswith(package+'/') and n.endswith(('.py','.json'))}
    need('nested_wheel_'+label,payloads==protocol[label+'_files'] and len(wheel.namelist())==len(payloads)+6 and len(wheel.namelist())==len(set(wheel.namelist())))
  expected_presentation=json.loads(z.read('artifact/presentation-inputs/expected-payloads.json'))['payloads']
  need('all37_presentation_commitments',len(expected_presentation)==37 and all(sha(z.read('artifact/paper/results/'+n))==d['sha256'] and z.getinfo('artifact/paper/results/'+n).file_size==d['bytes'] for n,d in expected_presentation.items()))
  owner=re.compile(r'(?i)(?:zzric|[A-Z]:[\\/]Users[\\/]|[A-Z]:[\\/]Projects(?:_data)?[\\/]|/Users/|/home/|drug_target_agents_data)')
  for name in names:
   if name==hgnc or Path(name).suffix not in ('.py','.json','.md','.toml','.lock','.txt','.csv','.svg','.bib'):continue
   text=z.read(name).decode('utf-8-sig')
   # Source code may contain fictional path/credential boundary fixtures; no
   # actual owner/project-root form is authorized in distributed text.
   if owner.search(text.replace('\\\\','\\')):privacy.append(dict(path=name,kind='owner_or_private_machine_root'))
   if re.search(r'sk-[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16}',text):privacy.append(dict(path=name,kind='credential_pattern'))
  need('text_privacy_scan',not privacy)
  readme=z.read('README.md').decode('utf-8');inner=z.read('artifact/README.md').decode('utf-8')
  need('outer_scope_and_corrected_command',all(s in readme for s in ('3,481','289.938','15.187','203.828','7.125','python -B -I','not a public deposit','Later','P10')) and '-B -I -m unittest' in inner)
  need('unknowns_declarations_science',q['owner_declarations']=='deferred' and q['publication_authorized'] is False and q['unsupported_or_unmeasured']['public_deposit'] is None
       and q['unsupported_or_unmeasured']['current_hosted_ci']=='not_executed' and q['unsupported_or_unmeasured']['total_physical_io_bytes'] is None and q['unsupported_or_unmeasured']['total_platform_cost_usd'] is None and q['scientific_validation']==q['study_independence']=='not_established')
 return dict(schema='p09.independent_release_zip_review.v1',status='PASS_POSITIVE_ALLOWLIST_ZIP_REVIEW' if not issues else 'FAIL_RELEASE_ZIP_REVIEW',check_count=len(checks),checks=checks,unresolved_findings=issues,privacy_findings=privacy,
  archive=dict(path=ZIP.relative_to(ROOT).as_posix(),sha256=sha(raw),bytes=len(raw),members=315,repeat_byte_identical=raw==repeat,manifest_sha256=MANIFEST,protocol_sha256=READY),
  public_qualification_sha256=sha(qraw),release_record_sha256=sha(record_raw),outer_README_sha256=sha(readme.encode('utf-8')),roles=dict(roles),
  scope=['Archive exact closure/hash/role/readback/retained-rights-document consistency; no legal certification or publication authorization.','CC0HGNC bytes were hashed inside the approved archive only, never parsed; no external originals reopened.','PDF/PNG bytes match reviewed commitments; no new PDF visual or font-rights review performed.','Current local qualification is supported Windows scope, not hosted CI/native Linux/fresh acquisition/scientific independence.','Frozen inner paper bytes remain older P08snapshot; future P10source/PDF versions must remain separate.'],originals_reopened=False,provider_payloads_parsed=False,tests_rerun=False,production_mutations=False)

if __name__=='__main__':
 report=run();target=ASSETS/'RELEASE-ZIP-CHECKS-v1.json'
 with target.open('xb') as stream:stream.write(json.dumps(report,indent=2).encode()+b'\n')
 print(json.dumps({k:report[k] for k in ('status','check_count','unresolved_findings','privacy_findings','archive')},indent=2))
