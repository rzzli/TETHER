"""Bounded offline tokenizer measurement; no server, generation or runtime edits."""
import ast,copy,hashlib,json,os,re,subprocess,time
from pathlib import Path
from asof.serde import canonical,encode,fingerprint
from asof.study.diagnostic import ACTIVE_SIMPLIFIED_SCHEMA
from asof.study.diagnostic_codec import quote_choices
P=Path(__file__).parent; BASE=P.parent; ROOT=P.resolve().parents[3]
CACHE=ROOT/'data/cache/r09-tokenizer-measurement-v1';CACHE.mkdir(exist_ok=False)
RULES=json.loads((P/'MEASUREMENT-PLAN-v2.json').read_bytes())
report={'schema_version':1,'role':'planning_only','plan_sha256':hashlib.sha256((P/'MEASUREMENT-PLAN-v2.json').read_bytes()).hexdigest(),'assets':[],'measurements':[],'generation_calls':0,'provider_spend_usd':0,'runtime_policy_changed':False}
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def checked(path,pin):
 assert path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256'],str(path)
 return json.loads(path.read_bytes())
def publish(name,value):
 with (P/name).open('xb') as f:f.write(canonical(value))
try:
 start=time.monotonic();inventory=json.loads((ROOT/'planning/review-assets/recovery-step5-20261026/inventory.json').read_bytes())
 assets=[a for a in inventory['assets'] if a['path'].lower().endswith(('.dll','.gguf','llama-tokenize.exe'))]
 for a in assets:
  path=Path(a['path']);before=path.stat();actual=sha(path);after=path.stat();assert actual==a['sha256'] and before.st_size==after.st_size==a['bytes'] and before.st_mtime_ns==after.st_mtime_ns
  report['assets'].append(dict(a,fresh_sha256=actual))
 report['asset_hash_seconds']=time.monotonic()-start;report['asset_hash_bytes']=sum(a['bytes'] for a in assets)
 publish('ASSET-CHECK.json',{'assets':report['assets'],'seconds':report['asset_hash_seconds'],'bytes':report['asset_hash_bytes']})
 exe=next(Path(a['path']) for a in assets if a['path'].endswith('llama-tokenize.exe'));model=next(Path(a['path']) for a in assets if '00001-of-00003.gguf' in a['path'])
 actual_dlls={x.resolve() for x in exe.parent.glob('*.dll')};assert actual_dlls=={Path(a['path']).resolve() for a in assets if a['path'].lower().endswith('.dll')}
 run=ROOT/'runs/r07-native-diagnostic-20261026T165505Z';assert sha(run/'terminal-seal.json')=='863bf2a9cfb8d4fd01a5223b993d87fbe2ac06992e7206d3d32ef4c712cf2d41';seal=json.loads((run/'terminal-seal.json').read_bytes())
 request=checked(run/'inputs/exposed-il6r-genetics-current/request.json',seal['files']['inputs/exposed-il6r-genetics-current/request.json']);assert fingerprint(request)=='14b735ef940bde56c04ea964cf145f3f7d1e343b2fe1e35de157cc8a5af2d61a'
 plan=json.loads((BASE/'PLAN-v2.json').read_bytes());assert fingerprint(plan)=='33d2b7dff7a3f834132b005be650129f0378cf74a1f3083dc60f8db2688e3a52'
 prompts=[]
 for fixture in ['synthetic-context','synthetic-orientation']:
  for stage in plan['asof_stages']+plan['stage_order']:
   spec=json.loads((BASE/(fixture+'-'+stage+'-v2.json')).read_bytes());assert fingerprint(spec['payload'])==spec['payload_sha256'];assert spec['original_request_sha256']==fingerprint(spec['semantic_data']['original_request'])
   prompts.append((fixture+':'+stage,'literal_stage',spec['payload']))
 aliases=encode(quote_choices(request));table=[{'source_id':a,'observation_id':request['source_request']['evidence'][i]['observation_id'],'pointers':list(c)} for i,(a,c) in enumerate(aliases.items())]
 schema=copy.deepcopy(encode(ACTIVE_SIMPLIFIED_SCHEMA));schema.pop('$comment',None);schema['properties']['claims']['maxItems']=request['source_request']['bounds']['max_claims'];cp=schema['properties']['claims']['items']['properties'];cp['source_ids']['items']={'type':'string','enum':list(aliases)};cp['quote_pointers']['items']={'type':'string','enum':sorted({p for c in aliases.values() for p in c})}
 expected=json.loads((BASE/'REAL-INPUT-FEASIBILITY.json').read_bytes())['stage_records']
 for stages in [plan['asof_stages'],plan['stage_order']]:
  for i,stage in enumerate(stages):
   data={'original_request':request,'original_source_table':table,'stage':stage,'prior_source_id_feedback':[{'stage':s,'source_ids':list(aliases)} for s in stages[:i]],'feedback_authority':'untrusted_generated_selection_not_evidence'}
   prompt='<|im_start|>system\n'+plan['guide']+'\n'+plan['role_guides'][stage]+'<|im_end|>\n<|im_start|>user\n'+canonical(data).decode().replace('<|','<\\u007c')+'<|im_end|>\n<|im_start|>assistant\n'
   payload={'prompt':prompt,'n_predict':1024,'temperature':0.0,'seed':42,'cache_prompt':False,'json_schema':schema,'stop':['<|im_end|>'],'stream':False};assert fingerprint(payload)==next(x['payload_sha256'] for x in expected if x['stage']==stage)
   prompts.append(('exposed-il6r:'+stage,'literal_stage',payload))
 auditpath=ROOT/'planning/review-assets/recovery-step7-20261026/post-run-mechanical-audit.json';audit=json.loads(auditpath.read_bytes());report['numeric_audit_sha256']=sha(auditpath)
 assert {x['cell_id']:x['measured_usage']['input_tokens'] for x in audit['cells']}==RULES['controls']
 for cell in RULES['controls']:
  name='cells/'+cell+'/payload.json';prompts.append((cell,'empirical_control',checked(run/name,seal['files'][name])))
 assert len(prompts)==24
 env={k:v for k,v in os.environ.items() if not k.startswith(('LLAMA_','HF_','HUGGING_FACE'))};env['LLAMA_ARG_OFFLINE']='1'
 argv=[str(exe),'--offline','--model',str(model),'--no-escape','--no-bos','--stdin','--ids','--show-count'];report['argv']=argv
 for idx,(name,kind,payload) in enumerate(prompts):
  raw=payload['prompt'].encode('utf-8');prefix=CACHE/str(idx).zfill(2);prefix.with_suffix('.prompt.bin').write_bytes(raw);t=time.monotonic()
  try:r=subprocess.run(argv,input=raw,capture_output=True,timeout=30,env=env,cwd=exe.parent)
  except subprocess.TimeoutExpired as e:
   prefix.with_suffix('.stdout.bin').write_bytes(e.stdout or b'');prefix.with_suffix('.stderr.bin').write_bytes(e.stderr or b'');raise
  prefix.with_suffix('.stdout.bin').write_bytes(r.stdout);prefix.with_suffix('.stderr.bin').write_bytes(r.stderr)
  assert r.returncode==0,(name,r.returncode)
  text=r.stdout.decode('utf-8');lists=re.findall(r'\[[\d, \r\n-]+\]',text);assert len(lists)==1,(name,'missing unique ID list')
  ids=ast.literal_eval(lists[0]);assert isinstance(ids,list) and all(type(x) is int and x>=0 for x in ids)
  other=text.replace(lists[0],'');counts=re.findall(r'(?:number of tokens|tokens|count)\s*[:=]\s*(\d+)',other,re.I)
  if not counts:counts=re.findall(r'^\s*(\d+)\s*$',other,re.M)
  assert len(counts)==1 and int(counts[0])==len(ids),(name,'count/id disagreement',other)
  item={'name':name,'kind':kind,'prompt_sha256':hashlib.sha256(raw).hexdigest(),'payload_sha256':fingerprint(payload),'prompt_utf8_bytes':len(raw),'byte_reservation':len(raw)+32,'cli_tokens':len(ids),'cli_tokens_plus32':len(ids)+32,'seconds':time.monotonic()-t,'stdout_sha256':hashlib.sha256(r.stdout).hexdigest(),'stderr_sha256':hashlib.sha256(r.stderr).hexdigest()}
  if kind=='empirical_control':item.update(expected_native_input_tokens=RULES['controls'][name],parity=len(ids)==RULES['controls'][name])
  report['measurements'].append(item)
  with (CACHE/'progress.jsonl').open('ab') as f:f.write(canonical(item)+b'\n')
  print(name,len(ids),flush=True)
 report['status']='complete';report['all_controls_exact']=all(x['parity'] for x in report['measurements'] if x['kind']=='empirical_control')
 report['aggregates']={n:{'cli_tokens':sum(x['cli_tokens'] for x in report['measurements'] if x['name'].startswith(n+':')),'cli_tokens_plus32':sum(x['cli_tokens_plus32'] for x in report['measurements'] if x['name'].startswith(n+':')),'byte_reservations':sum(x['byte_reservation'] for x in report['measurements'] if x['name'].startswith(n+':'))} for n in ['exposed-il6r','synthetic-context','synthetic-orientation']}
 publish('RESULT.json',report)
except BaseException as e:
 report.update(status='failed',error_type=type(e).__name__,error=str(e));publish('FAILURE.json',report);raise
