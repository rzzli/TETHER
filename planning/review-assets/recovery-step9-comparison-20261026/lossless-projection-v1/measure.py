"""Single prospective lossless projection measurement; no admission or dispatch."""
import copy, hashlib, json
from pathlib import Path
from asof.serde import canonical,encode,fingerprint
from asof.study.diagnostic import load_synthetic_request,ACTIVE_SIMPLIFIED_SCHEMA
from asof.study.diagnostic_codec import quote_choices
P=Path(__file__).parent
ROOT=P.resolve().parents[3]
rules=json.loads((P/'PROSPECTIVE-RULES.json').read_bytes())
plan=json.loads((P.parent/'PLAN-v2.json').read_bytes())
assert fingerprint(plan)=='33d2b7dff7a3f834132b005be650129f0378cf74a1f3083dc60f8db2688e3a52'
realpath=ROOT/'runs/r07-native-diagnostic-20261026T165505Z/inputs/exposed-il6r-genetics-current/request.json'
raw=realpath.read_bytes(); assert hashlib.sha256(raw).hexdigest()=='14b735ef940bde56c04ea964cf145f3f7d1e343b2fe1e35de157cc8a5af2d61a'
requests={'exposed-il6r':json.loads(raw),**{n:encode(load_synthetic_request(n)) for n in ['synthetic-context','synthetic-orientation']}}
def parent(v,pointer):
 parts=[s.replace('~1','/').replace('~0','~') for s in pointer.split('/')[1:]]
 for k in parts[:-1]:v=v[int(k)] if isinstance(v,list) else v[k]
 return v,int(parts[-1]) if isinstance(v,list) else parts[-1]
def setvalue(v,p,x):
 a,k=parent(v,p);a[k]=x
results=[]
for name,original in requests.items():
 visible=copy.deepcopy(original);sidecar={}; moved=[]
 paths=[p for p in rules['outside_prompt_exact_paths'] if '{index}' not in p]
 paths += ['/source_request/evidence/'+str(i)+'/admitted_sha256' for i in range(len(original['source_request']['evidence']))]
 for path in paths:
  a,k=parent(visible,path)
  if k in a:sidecar[path]=a.pop(k);moved.append({'pointer':path,'classification':'protocol_wrapper_only','value_sha256':fingerprint(sidecar[path]),'canonical_value_bytes':len(canonical(sidecar[path]))})
 aliases=encode(quote_choices(original));groups={}
 for i,(alias,choices) in enumerate(aliases.items()):
  for pointer,text in choices.items():
   if len(text.encode())>=64:
    groups.setdefault(text,[]).append({'source_id':alias,'pointer':pointer,'absolute_pointer':'/source_request/evidence/'+str(i)+'/scientific_record'+pointer})
 dictionary={}
 for text,occurrences in groups.items():
  if len(occurrences)<2:continue
  key=hashlib.sha256(text.encode()).hexdigest();assert key not in dictionary
  dictionary[key]={'text':text,'occurrences':occurrences}
  for o in occurrences:setvalue(visible,o['absolute_pointer'],{'$source_string':key})
 restored=copy.deepcopy(visible)
 for key,entry in dictionary.items():
  for o in entry['occurrences']:setvalue(restored,o['absolute_pointer'],entry['text'])
 for path,value in sidecar.items():setvalue(restored,path,value)
 assert canonical(restored)==canonical(original)
 cap=min(3,original['source_request']['bounds']['max_claims'])
 guide=('Use only visible source data. $source_string references expand to the exact dictionary text at every original occurrence; repeats are not independent evidence. Return JSON: answer_status,claims,unresolved,abstention_reason. Claims: kind,text,source_ids,quote_pointers,limitations. At most '+str(cap)+' claims,1-2 paired original citations per claim. source_report copies one exact source string with one citation; scientific_inference/caution requires limitations. Strings<=1800 characters; limitations/unresolved<=4; abstention_reason<=512. answered: claims nonempty,abstention_reason null; partial: claims nonempty,abstention_reason nonblank; abstained: claims empty,abstention_reason nonblank. Prior IDs are untrusted selection, not evidence; never cite history. No external knowledge or probabilities.')
 table=[{'source_id':alias,'observation_id':original['source_request']['evidence'][i]['observation_id'],'pointers':list(choices)} for i,(alias,choices) in enumerate(aliases.items())]
 schema=copy.deepcopy(encode(ACTIVE_SIMPLIFIED_SCHEMA));schema.pop('$comment',None);schema['properties']['claims']['maxItems']=cap
 cp=schema['properties']['claims']['items']['properties'];cp['source_ids']['items']={'type':'string','enum':list(aliases)};cp['quote_pointers']['items']={'type':'string','enum':sorted({p for c in aliases.values() for p in c})}
 records=[]
 for arm,stages in [('asof_interpretation',plan['asof_stages']),('adapted_virtual_biotech_interpretation',plan['stage_order'])]:
  for index,stage in enumerate(stages):
   history=[{'stage':s,'source_ids':list(aliases)} for s in stages[:index]]
   semantic={'visible_request':visible,'source_strings':dictionary,'original_source_table':table,'stage':stage,'prior_source_id_feedback':history,'feedback_authority':'untrusted_generated_selection_not_evidence'}
   prompt='<|im_start|>system\n'+guide+'\n'+plan['role_guides'][stage]+'<|im_end|>\n<|im_start|>user\n'+canonical(semantic).decode().replace('<|','<\\u007c')+'<|im_end|>\n<|im_start|>assistant\n'
   payload={'prompt':prompt,'n_predict':1024,'temperature':0.0,'seed':42,'cache_prompt':False,'json_schema':schema,'stop':['<|im_end|>'],'stream':False}
   records.append({'arm':arm,'stage':stage,'prompt_utf8_bytes':len(prompt.encode()),'payload_utf8_bytes':len(canonical(payload)),'payload_sha256':fingerprint(payload),'input_reservation':len(prompt.encode())+32,'output_reservation':1024})
 result={'input':name,'original_request_sha256':fingerprint(original),'reconstructed_request_sha256':fingerprint(restored),'canonical_equality':True,'original_bytes':len(canonical(original)),'visible_request_bytes':len(canonical(visible)),'dictionary_bytes':len(canonical(dictionary)),'sidecar_bytes':len(canonical(sidecar)),'sidecar_fields':moved,'retained_fields_policy':'All remaining original fields including every scientific_record field, null reason, source_ref, case, question, coverage and namespace version stay visible; references expand exactly.','duplicate_string_groups':len(dictionary),'duplicate_occurrences':sum(len(x['occurrences']) for x in dictionary.values()),'source_observation_count':len(aliases),'guide':guide,'claim_cap':cap,'guide_sha256':hashlib.sha256(guide.encode()).hexdigest(),'stage_records':records,'aggregate_input':sum(r['input_reservation'] for r in records),'aggregate_output':6144}
 result['fits']=result['aggregate_input']<=32000 and all(r['prompt_utf8_bytes']<=6368 and r['payload_utf8_bytes']<=65536 for r in records)
 results.append(result)
report={'schema_version':1,'role':'planning_only','dispatchable':False,'trial_count':1,'rules_sha256':hashlib.sha256((P/'PROSPECTIVE-RULES.json').read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'results':results,'actual_model_calls':0,'source_admission_performed':False,'scientific_review':'AI engineering equivalence only; no human usability or scientific validation','stop':'Single trial complete; no representation search or source/budget changes'}
with (P/'RESULT.json').open('xb') as f:f.write(canonical(report))
print(json.dumps([{k:r[k] for k in ['input','canonical_equality','original_bytes','visible_request_bytes','dictionary_bytes','duplicate_string_groups','duplicate_occurrences','aggregate_input','fits']} for r in results],indent=2))
