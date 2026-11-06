"""Read-only SC05 eligibility audit. No fitting, predictions or outcome scoring."""
from collections import defaultdict,Counter
from datetime import datetime,timezone
import hashlib,io,json,math,os
from pathlib import Path
import sys,tarfile,threading,time,unicodedata

ROOT=Path(__file__).resolve().parents[5]
OUT=ROOT/'data/cache'/('sc05-calibration-eligibility-audit-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
OUT.mkdir();START=time.monotonic();proofs=[];checked={}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def canonical(v):return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()
def load(path):return json.loads(Path(path).read_bytes())
def hashfile(path):
 with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def verify(path,expected,expected_bytes=None):
 path=Path(path);cachekey=(str(path.resolve()),expected,expected_bytes)
 if cachekey in checked:return checked[cachekey]
 actual=hashfile(path);size=path.stat().st_size
 assert actual==expected,(str(path),'hash mismatch');assert expected_bytes is None or size==expected_bytes
 p=dict(path=str(path.resolve()),bytes=size,sha256=actual);proofs.append(p);checked[cachekey]=p;return p
def checkproof(p):return verify(p['path'],p['sha256'],p.get('bytes'))
def norm(s):return ' '.join(unicodedata.normalize('NFKC',s).casefold().split())
def write(name,v):
 with (OUT/name).open('xb') as stream:stream.write(json.dumps(v,sort_keys=True,indent=2).encode()+b'\n')
def timeout():
 write('TIMEOUT.json',dict(status='timeout',elapsed_seconds=time.monotonic()-START));os._exit(124)
timer=threading.Timer(285,timeout);timer.daemon=True;timer.start()
try:
 prep=ROOT/'data/benchmark/scifact/preparation-20261105-attempt03';pm=load(prep/'manifest.json')
 verify(prep/'manifest.json','cb32f1384c49b66b912a62120abd7137a8a19b303f3ad052f035f21779c131f8')
 archive=pm['archive'];verify(archive['path'],archive['sha256'],archive['bytes']);verify(archive['receipt_path'],archive['receipt_sha256'])
 contents={}
 with tarfile.open(archive['path'],'r:gz') as tar:
  for name,expected in pm['members'].items():
   raw=tar.extractfile(name).read();assert sha(raw)==expected['sha256'] and len(raw)==expected['bytes'];contents[name]=[json.loads(line) for line in raw.splitlines()]
 products={}
 for name,p in pm['products'].items():
  path=prep/p['path'];verify(path,p['sha256'],p['bytes'])
  products[name]=[json.loads(line) for line in path.read_bytes().splitlines()] if p['format']=='jsonl' else load(path)
 split=products['split'];train=contents['data/claims_train.jsonl'];dev=contents['data/claims_dev.jsonl'];allclaims={r['id']:r for r in train+dev};origins={r['id']:'train' for r in train};origins.update({r['id']:'dev' for r in dev})
 owners=defaultdict(set)
 for key,r in allclaims.items():
  for d in set(r['cited_doc_ids'])|{int(k) for k in r['evidence']}:owners['doc:'+str(d)].add(key)
  owners['text:'+sha(norm(r['claim']).encode())].add(key)
 neighbours={key:set() for key in allclaims}
 for ids in owners.values():
  for key in ids:neighbours[key].update(ids-{key})
 seen=set();groups=[]
 for root in sorted(allclaims):
  if root in seen:continue
  stack=[root];group=set()
  while stack:
   key=stack.pop()
   if key in group:continue
   group.add(key);stack.extend(neighbours[key]-group)
  seen.update(group);ids=sorted(group);gid=sha(canonical(ids))
  groups.append(dict(group_id=gid,claim_ids=ids,train_ids=[k for k in ids if origins[k]=='train'],dev_ids=[k for k in ids if origins[k]=='dev']))
 eligible=sorted((g for g in groups if not g['dev_ids']),key=lambda g:(sha(f"20261105:{g['group_id']}".encode()),g['group_id']))
 for index,g in enumerate(eligible):g['partition']='fit' if index<int(len(eligible)*.70) else 'tune' if index<int(len(eligible)*.85) else 'calibration'
 for g in groups:
  if g['dev_ids']:g['partition']='dev_connected'
 assert sorted(groups,key=lambda g:g['group_id'])==split['groups'],'Independent source/text components differ'
 parts={name:[] for name in split['partitions']}
 for g in groups:
  for key in g['claim_ids']:
   name=g['partition'] if g['partition']!='dev_connected' else 'dev' if origins[key]=='dev' else 'quarantined_train';parts[name].append(key)
 for ids in parts.values():ids.sort()
 assert parts==split['partitions']
 cal=set(parts['calibration']);caltext={norm(allclaims[k]['claim']) for k in cal};caldocs=set().union(*(set(allclaims[k]['cited_doc_ids'])|{int(d) for d in allclaims[k]['evidence']} for k in cal))
 for part in ('fit','tune','calibration','dev'):
  expected=[{k:allclaims[key][k] for k in ('id','claim')} for key in parts[part]];assert expected==products['queries_'+part]
  expectedrefs=[{k:allclaims[key][k] for k in ('id','claim','evidence','cited_doc_ids')} for key in parts[part]]
  assert canonical(expectedrefs)==canonical(products['references_'+part]),'Original opaque reference projection differs'
 overlaps={}
 for name in ('fit','tune','dev','quarantined_train'):
  docs=set().union(*(set(allclaims[k]['cited_doc_ids'])|{int(d) for d in allclaims[k]['evidence']} for k in parts[name]))
  texts={norm(allclaims[k]['claim']) for k in parts[name]}
  overlaps[name]=dict(ids=len(cal&set(parts[name])),annotated_documents=len(caldocs&docs),normalized_claim_texts=len(caltext&texts))
  assert not any(overlaps[name].values())
 calgroups=[g for g in groups if g['partition']=='calibration'];assert len(cal)==69 and len(calgroups)==49
 forbidden={str((prep/pm['products'][name]['path']).resolve()).casefold() for name in ('queries_calibration','references_calibration')}
 base=ROOT/'data/benchmark/scifact/native-20261105T234805Z-attempt01';verify(base/'RECEIPT.json','3a997165aac2f0a85a93890f5e10a66d8117563e380e98f892dd3cb8a93f8968');br=load(base/'RECEIPT.json')
 for name,digest in br['outputs'].items():verify(base/name,digest)
 baserecipes=[];baselineforbidden=0;baselineauditevents=0
 for path in sorted((base/'recipes').glob('*.json'))+sorted((base/'evaluation-jobs').glob('*/recipe.json')):
  value=load(path)
  for p in value['inputs'].values():checkproof(p);assert str(Path(p['path']).resolve()).casefold() not in forbidden
  assert not cal.intersection(value['schedule'])
  if value['mode']=='fit':
   assert set(value['inputs'])=={'corpus','queries_fit','fit_pairs'}
   assert {r['id'] for r in products['queries_fit']}==set(parts['fit'])
   assert {r['claim_id'] for r in products['fit_pairs']}<=set(parts['fit'])
  baserecipes.append(dict(path=str(path),mode=value['mode'],scheduled=len(value['schedule']),input_names=list(value['inputs'])))
 for path in sorted(base.glob('jobs/*/io-audit.jsonl'))+sorted(base.glob('evaluation-jobs/*/io-audit.jsonl')):
  for line in path.read_bytes().splitlines():
   row=json.loads(line);baselineauditevents+=1;assert row['allowed'] is True
   if row.get('path') and str(Path(row['path']).resolve()).casefold() in forbidden:baselineforbidden+=1
 assert baselineforbidden==0
 print(json.dumps(dict(stage='baseline_and_original_split_checked',files=len(proofs))),flush=True)
 acceptance=ROOT/'planning/review-assets/tether-semantic-20261106/sc03/root-acceptance-attempt01/ROOT-ACCEPTANCE.json'
 verify(acceptance,'4425db2f0300713ffc397cdd79445a4a9fe383d6f85820f145add22a1372a95f');acc=load(acceptance)
 for path,digest in acc['anchors'].items():verify(path,digest)
 frame=load(ROOT/'planning/review-assets/tether-semantic-20261106/sc03/production-freeze-attempt01/EXPERIMENT.json')
 for p in frame['pins']:checkproof(p)
 checkproof(frame['model']);external=load(frame['model']['path'])
 assert external['local_fitting_performed'] is False and external['configuration']['method']=='multivers_fever_sci_zero_shot'
 assert external['acquisition_receipt']['sha256']=='a76d300564d0a5a4477a31cf167748e2e5b8540696b1c836d0fb8fab537b1610'
 for p in external['runtime_source_pins']+[external['producer_code'],external['acquisition_receipt']]:checkproof(p)
 for p in frame['conditions'].values():
  checkproof(p)
  for pin in load(p['path'])['pins']:checkproof(pin)
 anchors=load(ROOT/'planning/review-assets/tether-semantic-20261106/sc03/production-freeze-attempt01/execution/RESULT-ANCHORS.json')
 condition_checks={};primary_vectors=0;rationale_values=0
 for condition,description in anchors['conditions'].items():
  checkproof(description['worker_receipt']);checkproof(description['supervisor_outcome']);location=Path(description['worker_receipt']['path']).parent;receipt=load(location/'RECEIPT.json')
  assert receipt['status']=='complete'
  for name,p in receipt['files'].items():verify(location/name,p['sha256'],p['bytes'])
  recipe=load(location/'recipe.json');checkproof(recipe['requests']);assert set(recipe['schedule'])==set(parts['dev']) and not cal.intersection(recipe['schedule'])
  assert recipe['acquisition_receipt_sha256']==external['acquisition_receipt']['sha256']
  assert Path(recipe['acquisition_root']).resolve()==Path(external['acquisition_receipt']['path']).resolve().parent
  requests=[json.loads(line) for line in Path(recipe['requests']['path']).read_bytes().splitlines()]
  assert [r['id'] for r in requests]==recipe['schedule']==parts['dev']
  assert all(r['claim']==allclaims[r['id']]['claim'] for r in requests)
  assert not caltext.intersection(norm(r['claim']) for r in requests)
  useddocs={d['doc_id'] for r in requests for d in r['documents']};source_overlap=caldocs&useddocs
  condition_checks[condition]=dict(claims=len(requests),calibration_claim_or_exact_text_overlap=0,
   calibration_annotated_documents_seen_as_input=len(source_overlap),claims_using_any_calibration_document=sum(any(d['doc_id'] in caldocs for d in r['documents']) for r in requests),
   calibration_claims_connected_to_seen_documents=sum(bool((set(allclaims[k]['cited_doc_ids'])|{int(d) for d in allclaims[k]['evidence']})&source_overlap) for k in cal),
   worker_receipt_sha256=description['worker_receipt']['sha256'],requests_sha256=recipe['requests']['sha256'])
  if condition=='primary':
   by_id={r['id']:r for r in requests}
   for path in (location/'pairs').glob('*.json'):
    value=load(path);assert value['status']=='completed';prediction=value['prediction'];lp=prediction['label_probs'];rp=prediction['rationale_probs']
    assert len(lp)==3 and all(type(v) in (float,int) and math.isfinite(v) and 0<=v<=1 for v in lp) and abs(sum(lp)-1)<1e-5
    doc=next(d for d in by_id[value['claim_id']]['documents'] if d['doc_id']==value['abstract_id'])
    assert len(rp)==len(doc['abstract'])==len(value['observations']['sentence_offsets']) and all(type(v) in (float,int) and math.isfinite(v) and 0<=v<=1 for v in rp)
    assert prediction['predicted_label']==external['configuration']['label_order'][max(range(3),key=lp.__getitem__)]
    assert prediction['predicted_rationale']==[i for i,p in enumerate(rp) if p>=.5]
    primary_vectors+=1;rationale_values+=len(rp)
 assert primary_vectors==1500
 print(json.dumps(dict(stage='all_sc03_input_receipts_and_probability_shapes_checked',files=len(proofs))),flush=True)
 qchecks=[]
 for folder in sorted((ROOT/'data/benchmark/scifact_multivers').glob('qualification-*')):
  controlpath=folder/'controls.json'
  assert controlpath.read_bytes()==(ROOT/'experiments/scifact_multivers/fictional-controls.json').read_bytes()
  verify(controlpath,'65a697882396742b46589bfd96f1a18c3862583447f202560dea1d6a3a6ada2e')
  inputs=list(folder.glob('*.input.json'));observed=[]
  for path in inputs:
   value=load(path);assert norm(value['claim']) not in caltext;observed.append(value['id'])
  qchecks.append(dict(root=str(folder),input_cases=len(inputs),calibration_exact_claim_text_overlap=0,ids=observed,exact_fictional_controls_match=True))
 freeze=load(ROOT/'planning/review-assets/tether-semantic-20261106/solver-qualification/full-freeze-attempt02/MANIFEST.json')
 small_pin_checks=0
 for p in freeze['pins']:
  if p['bytes']<=16*1024**2:checkproof(p);small_pin_checks+=1
 controls=load(ROOT/'experiments/scifact_multivers/fictional-controls.json')
 assert not caltext.intersection(norm(c['claim']) for c in controls['cases'])
 acq=ROOT/'data/cache/tether-multivers-acquisition-20261106-attempt01/RECEIPT.json';verify(acq,'a76d300564d0a5a4477a31cf167748e2e5b8540696b1c836d0fb8fab537b1610');cp=next(p for p in load(acq)['files'] if p['kind']=='checkpoint')
 assert cp['logical_id']=='fever_sci.ckpt' and cp['http_version_id']=='GYe58tFsyvvn1n7rib5H4wrsiq32ZY5Y'
 checkpoint_started=time.monotonic();checkproof(cp);checkpoint_hash_seconds=time.monotonic()-checkpoint_started
 roles={name:pm['products'][name]['purposes'] for name in ('queries_calibration','references_calibration','corpus')}
 assert 'calibrate' in roles['queries_calibration'] and 'calibrate' in roles['references_calibration']
 assert all(p not in roles[name] for name in ('queries_calibration','references_calibration') for p in ('fit','tune','predict'))
 result=dict(kind='sc05_calibration_local_eligibility_audit',status='conditional_local_eligibility_supported',created_at_utc=datetime.now(timezone.utc).isoformat(),
 elapsed_seconds=time.monotonic()-START,calibration_claims=len(cal),calibration_groups=len(calgroups),group_size_distribution=dict(Counter(len(g['claim_ids']) for g in calgroups)),
 calibration_annotated_documents=len(caldocs),partition_counts={k:len(v) for k,v in parts.items()},partition_overlap=overlaps,
 original_archive_and_projection_reconstructed=True,baseline=dict(receipts_verified=True,recipe_count=len(baserecipes),recipes=baserecipes,io_audit_events=baselineauditevents,calibration_product_reads=baselineforbidden,
  scope='Retained fit/tune/dev workers and tuning scorers; full public corpus was an authorized shared input. Preparation/reference auditing is not label-free global non-access.'),
 sc03_conditions=condition_checks,sc03_current_code_and_frame_pins_verified=True,sc03_model_configuration=external['configuration'],sc02_qualification=qchecks,small_qualification_pins_verified=small_pin_checks,
 probabilities=dict(primary_pair_label_probability_vectors=primary_vectors,primary_sentence_probabilities=rationale_values,finite_range_and_dimensions_verified=True,
  calibration_outputs_in_examined_runs=False,release_decode_reconstructed=True,scope='Shape, release decode and preservation checks only; no scalar confidence, correctness, threshold or reliability computation.'),
 checkpoint=dict(path=cp['path'],bytes=cp['bytes'],sha256=cp['sha256'],s3_version_id=cp['http_version_id'],fresh_weight_hash_verified=True,hash_seconds=checkpoint_hash_seconds),
 purpose_roles=roles,inference_calls=0,fitting_performed=False,calibration_outcome_analysis=False,
 limits=['Public benchmark training claims; globally untouched/contamination-free status is not established.',
 'All5183 corpus abstracts were available to the baseline/index; retrieved-document exposure is separate from claim/label fitting.',
 'SC03 has explicit bounded input recipes and frozen source, not independent OS-level no-access attestation.',
 'Original supervised containers and reference projections are read here for provenance/source grouping; outcomes are not interpreted for selection or calibration.',
 'Pre-SciFact-finetuning checkpoint status does not exclude encoder/weak-supervision/model-development overlap.',
 'A new calibrate-purpose controller and frozen scalar/endpoint/regularization protocol are required before69-case inference and fitting.'])
 write('PROOFS.json',dict(files=proofs,checked_entries=len(proofs),unique_paths=len({p['path'] for p in proofs})))
 write('REPORT.json',result);timer.cancel();print(json.dumps(dict(report=str(OUT/'REPORT.json'),report_sha256=hashfile(OUT/'REPORT.json'),elapsed=result['elapsed_seconds'],probability_vectors=primary_vectors,conditions=condition_checks)),flush=True)
except BaseException as error:
 timer.cancel();write('FAILURE.json',dict(error_type=type(error).__name__,message=str(error),elapsed_seconds=time.monotonic()-START,verified_proofs=len(proofs)));raise
