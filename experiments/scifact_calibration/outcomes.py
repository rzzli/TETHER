"""Evaluator-only, source-bound reconstruction of strict SciFact outcomes.

No model, retrieval or fitting is executed here. Externally anchored frames name
one complete partition; development references require an already sealed map.
The independent strict criterion is compared with the maintained scorer only
after the prediction, source and reference records have been reconstructed.
"""
from collections.abc import Mapping
from dataclasses import dataclass
import io
import math
import os
from pathlib import Path, PurePosixPath
import tarfile

from tether_engine.serde import canonical, encode, freeze, parse_json
from . import calibration as numerical
from .inputs import capture, digest, local_path, need, original_locator

ROOT=Path(__file__).resolve().parents[2]
KIND='sc05_source_bound_outcomes_v1'
POLICY='exact_documents_labels_complete_native_capped_rationale_v1'
MAX_FILE=64*1024**2
MAX_TOTAL=2*1024**3
DEPENDENCY_POLICY=freeze(dict(ipv6_import_probe='disabled_without_socket_call',
    project_distribution_discovery='exact_project_import_roots_excluded',
    windows_version_probe='native_fallback_without_shell' if os.name=='nt' else 'not_applicable',
    network_and_child_audit='unconditionally_denied',sys_path_modified=False))


def _same(a,b):return canonical(a)==canonical(b)
def _integer(value):return type(value) is int and value>=0
def _finite(value):return type(value) in (int,float) and math.isfinite(value) and value>=0


def _sentence_bindings(actual,expected):
    """Compare exact unique source locators, independent of JSON map order.

    The retained schema-one admission checker indexes bindings by document and
    sentence. A freshly assembled prediction follows retrieval order, while an
    archived canonical JSON prediction orders its document keys differently.
    Source identity and text bytes are unchanged by that representation choice.
    """
    def indexed(rows):
        need(isinstance(rows,(list,tuple)),'Sentence binding list required')
        found={}
        for row in rows:
            need(isinstance(row,Mapping) and set(row)=={'doc_id','sentence_id','text_sha256'} and
                 type(row['doc_id']) is int and row['doc_id']>0 and type(row['sentence_id']) is int and
                 row['sentence_id']>=0 and isinstance(row['text_sha256'],str),'Sentence binding schema differs')
            key=(row['doc_id'],row['sentence_id'])
            need(key not in found,'Duplicate sentence binding')
            found[key]=row['text_sha256']
        return found
    return indexed(actual)==indexed(expected)


def _name(value):
    need(isinstance(value,str) and value and '\\' not in value and ':' not in value,
         'Safe POSIX member name required')
    parts=value.split('/')
    need(not value.startswith('/') and all(p not in ('','.','..') and not p.endswith((' ','.')) for p in parts),
         'Unsafe receipt member')
    return PurePosixPath(value)


def _json_lines(raw):
    need(raw.endswith(b'\n'),'Truncated JSONL')
    lines=raw.splitlines();need(lines and len(lines)<=100000,'Bounded nonempty JSONL required')
    need(all(line and len(line)<=1024**2 for line in lines),'Invalid JSONL member')
    return [parse_json(line) for line in lines]


class _Capture:
    """One-buffer proof reads with a final no-change pass over all inputs."""
    def __init__(self):self.proofs={};self.total=0
    def read(self,proof,maximum=MAX_FILE):
        raw=capture(proof,maximum);path=str(local_path(proof['path']))
        if path in self.proofs:need(_same(self.proofs[path],proof),'Conflicting proofs for one path')
        else:
            self.total+=len(raw);need(self.total<=MAX_TOTAL,'Outcome input total byte cap')
            self.proofs[path]=freeze(encode(proof))
        return raw
    def json(self,proof,maximum=MAX_FILE):return parse_json(self.read(proof,maximum))
    def finish(self):
        for proof in self.proofs.values():capture(proof,MAX_FILE)
        return tuple(self.proofs.values())


def _inventory(reader,root,receipt_proof,*,legacy=False):
    root=local_path(root);need(root.is_dir(),'Missing sealed producer root')
    need(local_path(receipt_proof['path'])==root/'RECEIPT.json','Receipt/root identity differs')
    receipt=reader.json(receipt_proof,8*1024**2)
    need(isinstance(receipt,dict) and isinstance(receipt.get('files'),dict) and receipt['files'], 'Sealed inventory required')
    need(receipt.get('status')==('complete' if legacy else 'completed'),'Producer not terminal complete')
    proofs={};buffers={}
    for name,spec in receipt['files'].items():
        _name(name);need(name!='RECEIPT.json' and len(proofs)<10000,'Invalid inventory size or self-reference')
        need(isinstance(spec,dict) and set(spec) in ({'bytes','sha256'},{'path','bytes','sha256'}),'Receipt proof fields')
        path=local_path(root/name)
        need(path.is_relative_to(root) and ('path' not in spec or local_path(spec['path'])==path),'Receipt path binding differs')
        proof=dict(path=str(path),bytes=spec['bytes'],sha256=spec['sha256'])
        buffers[name]=reader.read(proof);proofs[name]=proof
    actual=set()
    for path in root.rglob('*'):
        local_path(path)
        if path.is_dir():continue
        need(path.is_file() and len(actual)<10002,'Nonregular or excessive producer files')
        actual.add(path.relative_to(root).as_posix())
    extras={'journal.jsonl','events.jsonl'} if legacy else set()
    need(actual==set(proofs)|extras|{'RECEIPT.json'},'Producer inventory contains missing or extra files')
    if legacy:
        # Journal is anchored by the original receipt's terminal chain; event
        # signals are reconstructed separately and never used as source truth.
        for name in extras:
            path=local_path(root/name);size=path.stat().st_size
            need(size<=MAX_FILE,'Legacy event bound')
            with path.open('rb') as stream:raw=stream.read(MAX_FILE+1)
            need(len(raw)==size,'Legacy event changed while captured')
            proof=dict(path=str(path),bytes=size,sha256=digest(raw))
            reader.read(proof);proofs[name]=proof;buffers[name]=raw
    return receipt,proofs,buffers


def _chain(raw):
    previous='0'*64;events=[];last=-math.inf
    for row in _json_lines(raw):
        need(isinstance(row,dict) and set(row)=={'sequence','previous_sha256','event','monotonic_seconds','details','sha256'},'Journal fields')
        recorded=row['sha256'];body={k:v for k,v in row.items() if k!='sha256'}
        need(type(row['sequence']) is int and row['sequence']==len(events) and row['previous_sha256']==previous and
             digest(canonical(body))==recorded and _finite(row['monotonic_seconds']) and row['monotonic_seconds']>=last,
             'Journal chain/order differs')
        need(isinstance(row['details'],dict),'Journal detail object required')
        previous=recorded;last=row['monotonic_seconds'];events.append(row)
    return events,previous


def _preparation(reader,transition,partition):
    """Read only selected original annotation members, never the other split.

    The external transition anchors the previously audited projection and split.
    This reader rechecks the selected original bytes and field projections. It
    does not rerun the mixed-role preparation audit during calibration scoring.
    """
    frame=reader.json(transition,1024**2)
    need(frame['kind']=='sc05_preparation_transition_v1' and frame['purpose']=='calibrate','Wrong preserved source transition')
    manifest=reader.json(frame['manifest']);base=local_path(frame['manifest']['path']).parent
    need(manifest['kind']=='scifact_preparation' and manifest['authority_version']=='purpose_field_projection_v1','Wrong source authority')
    archive_raw=reader.read(frame['archive']);receipt=reader.json(frame['archive_receipt']);acquisition=reader.json(frame['acquisition'])
    entries=[r for r in acquisition['originals'] if Path(r['file']).name=='scifact-data.tar.gz']
    need(len(entries)==1,'Exactly one original acquisition archive');entry=entries[0]
    original_root=local_path(frame['original_repository_root'])
    archive_path=original_locator(entry['file'],original_root);receipt_path=original_locator(entry['receipt_file'],original_root)
    need(archive_path==local_path(frame['archive']['path']) and entry['sha256']==frame['archive']['sha256'] and entry['bytes']==frame['archive']['bytes'] and
         receipt_path==local_path(frame['archive_receipt']['path']) and entry['receipt_sha256']==frame['archive_receipt']['sha256'] and
         receipt['status']=='downloaded_not_parsed' and original_locator(receipt['path'],original_root)==archive_path and receipt['sha256']==entry['sha256'] and
         receipt['bytes']==entry['bytes'] and receipt['url']==entry['source_url'],'Original acquisition/transport binding')
    archived=manifest['archive']
    need(all(archived[k]==frame['archive'][k] for k in ('path','bytes','sha256')) and
         archived['receipt_path']==frame['archive_receipt']['path'] and archived['receipt_sha256']==frame['archive_receipt']['sha256'] and
         archived['physical_role']=='mixed_role_preparation_container' and
         archived['allowed_purposes']==['prepare','preparation_audit'],'Mixed source authority changed')
    wanted={'data/corpus.jsonl','data/claims_'+('train' if partition=='calibration' else 'dev')+'.jsonl'}
    captured={};seen=set();expanded=0
    with tarfile.open(fileobj=io.BytesIO(archive_raw),mode='r:gz') as archive:
        for item in archive:
            _name(item.name);need(item.name not in seen and len(seen)<100 and (item.isfile() or item.isdir()),'Archive member/type differs')
            seen.add(item.name);expanded+=item.size
            need(0<=item.size<=16*1024**2 and expanded<=MAX_FILE,'Expanded source bound')
            if item.name in wanted:
                need(item.isfile(),'Selected source member must be regular')
                with archive.extractfile(item) as stream:raw=stream.read(item.size+1)
                need(len(raw)==item.size and _same(dict(bytes=len(raw),sha256=digest(raw)),manifest['members'][item.name]),'Original member proof differs')
                captured[item.name]=_json_lines(raw)
    need(set(captured)==wanted,'Missing original annotation member')
    corpus=sorted(({k:row[k] for k in ('doc_id','title','abstract')} for row in captured['data/corpus.jsonl']),key=lambda x:x['doc_id'])
    originals={}
    for row in captured[next(name for name in wanted if 'claims_' in name)]:
        need(type(row['id']) is int and row['id'] not in originals,'Duplicate original claim identity')
        originals[row['id']]={k:row[k] for k in ('id','claim','evidence','cited_doc_ids')}
    return frame,manifest,base,corpus,originals


def strict_outcome(gold,prediction,*,produced,admitted,corpus):
    """Independent exact-document/label and allowed rationale-prefix criterion."""
    need(type(produced) is bool and type(admitted) is bool and (produced or not admitted),'Operational outcome states')
    need(type(gold['id']) is int and isinstance(gold['evidence'],Mapping),'Canonical gold identity')
    for key,sets in gold['evidence'].items():
        need(isinstance(key,str) and key.isdecimal() and str(int(key))==key and int(key) in corpus and sets,'Gold document binding')
        labels=set();seen=set()
        for item in sets:
            need(set(item)=={'label','sentences'} and item['label'] in ('SUPPORT','CONTRADICT'),'Gold label schema')
            indices=item['sentences'];need(isinstance(indices,(list,tuple)) and indices and len(set(indices))==len(indices) and
                all(_integer(i) and i<len(corpus[int(key)]['abstract']) for i in indices) and not seen.intersection(indices),'Gold rationale indices')
            labels.add(item['label']);seen.update(indices)
        need(len(labels)==1,'Conflicting gold labels')
    if not produced:
        need(prediction is None,'Unproduced candidate cannot have a prediction')
        return 0
    need(isinstance(prediction,Mapping) and set(prediction)=={'id','evidence'} and
         type(prediction['id']) is int and prediction['id']==gold['id'] and isinstance(prediction['evidence'],Mapping),
         'Prediction identity/schema')
    for key,item in prediction['evidence'].items():
        need(isinstance(key,str) and key.isdecimal() and str(int(key))==key and int(key) in corpus and
             set(item)=={'label','sentences'} and item['label'] in ('SUPPORT','CONTRADICT'),'Predicted document/label')
        indices=item['sentences'];need(isinstance(indices,(tuple,list)) and list(indices)==sorted(set(indices)) and
             all(_integer(i) and i<len(corpus[int(key)]['abstract']) for i in indices),'Prediction rationale outside source')
    if not admitted or set(gold['evidence'])!=set(prediction['evidence']):return 0
    for key,alternatives in gold['evidence'].items():
        candidate=prediction['evidence'][key]
        if any(item['label']!=candidate['label'] for item in alternatives):return 0
        allowance=max(3,min(len(item['sentences']) for item in alternatives))
        prefix=tuple(candidate['sentences'])[:allowance]
        if not any(all(sentence in prefix for sentence in item['sentences']) for item in alternatives):return 0
    return 1


def _native_pair(pair,request,document):
    cid,did=request['id'],document['doc_id']
    need(type(pair['claim_id']) is int and type(pair['abstract_id']) is int and
         (pair['claim_id'],pair['abstract_id'])==(cid,did) and pair['input_document_sha256']==digest(canonical(document)),
         'Pair source identity differs')
    if pair['status']!='completed':
        need(pair['status'] in ('overlength','input_unavailable') and pair['prediction'] is None and pair['model_dispatch'] is False,
             'Unknown or fabricated incomplete pair')
        if pair['status']=='input_unavailable':need(not document['abstract'],'Unavailable input has source text')
        else:need(pair['reason']=='Input exceeds 4096 tokens; no truncation is permitted','Unexpected native failure')
        return None
    need(pair['model_dispatch'] is True,'Completed pair lacks dispatch')
    prediction=pair['prediction'];fields={'claim_id','abstract_id','predicted_label','predicted_rationale','label_probs','rationale_probs'}
    need(isinstance(prediction,dict) and set(prediction)==fields and type(prediction['claim_id']) is int and
         type(prediction['abstract_id']) is int and (prediction['claim_id'],prediction['abstract_id'])==(cid,did),'Native identity/schema')
    ps=prediction['label_probs'];rp=prediction['rationale_probs']
    valid=lambda x:type(x) in (int,float) and math.isfinite(x) and 0<=x<=1
    need(isinstance(ps,list) and len(ps)==3 and all(valid(p) for p in ps) and abs(math.fsum(ps)-1)<=1e-5,'Native label probabilities')
    need(prediction['predicted_label']==('CONTRADICT','NEI','SUPPORT')[max(range(3),key=ps.__getitem__)],'Native label decode')
    need(isinstance(rp,list) and len(rp)==len(document['abstract']) and all(valid(p) for p in rp) and
         isinstance(prediction['predicted_rationale'],list) and all(type(i) is int for i in prediction['predicted_rationale']) and
         prediction['predicted_rationale']==[i for i,p in enumerate(rp) if p>=.5],'Native rationale decode/source length')
    observations=pair['observations'];need(isinstance(observations,dict) and type(observations.get('token_count')) is int and
         0<observations['token_count']<=4096,'Native token accounting')
    return prediction


def _read_worker(reader,descriptor,requests,partition):
    legacy=partition=='dev';root=local_path(descriptor['root'])
    receipt,proofs,raws=_inventory(reader,root,descriptor['receipt'],legacy=legacy)
    parsed={name:parse_json(raw) for name,raw in raws.items() if name.endswith('.json')}
    recipe=parsed['recipe.json'];condition='primary' if legacy else 'calibration'
    # Producer recipe formatting differs from the external original file. Its
    # canonical value and external proof are both captured, never inferred.
    original=reader.read(descriptor['recipe'],1024**2)
    need(_same(parse_json(original),recipe) and receipt['recipe_sha256']==descriptor['recipe']['sha256'] and
         recipe['schedule']==[r['id'] for r in requests] and recipe['requests']==descriptor['requests'],'Producer recipe/source binding')
    need(type(recipe['schema_version']) is int and recipe['schema_version']==1 and
         recipe['kind']==('sc03_condition_worker' if legacy else 'sc05_calibration_worker_v1'),'Producer recipe kind differs')
    need(recipe.get('condition')=='primary' if legacy else recipe.get('purpose')=='calibrate','Worker role differs')
    need(type(recipe['pair_seconds']) in (int,float) and 0<recipe['pair_seconds']<=120,'Pair deadline differs')
    model=parsed['MODEL.json'];params=model['metadata']['hparams']
    need(params.get('label_threshold') is None and params.get('rationale_threshold')==.5 and
         params.get('num_labels',3)==3,'Qualified native decode configuration differs')
    events,last=_chain(raws['journal.jsonl'])
    if legacy:need(receipt['journal_records']==len(events) and receipt['journal_last_sha256']==last and
                   receipt['requests_sha256']==descriptor['requests']['sha256'],'Original journal receipt anchor')
    else:
        status=parsed['STATUS.json']
        need(receipt['kind']=='sc05_calibration_worker_receipt_v1' and status['kind']=='sc05_calibration_worker_status_v1' and
             status['status']=='completed' and status['recipe_sha256']==receipt['recipe_sha256'] and
             status['error'] is None and status['references_read'] is False and status['scientific_scoring_performed'] is False and
             status['automatic_retry'] is False and status['hard_deadline'] is False and type(status['io_denials']) is int and status['io_denials']==0,
             'Calibration worker policy failed')
        need(_same(status['files'],{name:proof for name,proof in proofs.items() if name!='STATUS.json'}),'Status inventory differs')
        audit=_json_lines(raws['io-audit.jsonl'])
        need(all(row.get('allowed') is True for row in audit),'Worker recorded denied I/O')
    indexed={}
    for event in events:
        d=event['details'];key=(event['event'],d.get('claim_id'),d.get('abstract_id'))
        need(('claim_id' not in d or type(d['claim_id']) is int) and
             ('abstract_id' not in d or type(d['abstract_id']) is int),'Noncanonical journal identity')
        indexed.setdefault(key,[]).append(d)
    def one(name,cid=None,did=None):
        found=indexed.get((name,cid,did),[]);need(len(found)==1,'Missing/duplicate producer event: '+name);return found[0]
    admitted=one('inputs_admitted');need(admitted['requests_sha256']==descriptor['requests']['sha256'] and admitted['references_read'] is False,'Worker input admission differs')
    terminal='condition_completed' if legacy else 'calibration_completed'
    need(events[-1]['event']==terminal,'Nonterminal or failed worker journal')
    expected_events={'inputs_admitted','claim_started','pair_started','pair_completed','pair_failed','pair_unavailable','pair_committed','claim_committed',terminal}
    if not legacy:
        expected_events|={'calibration_reserved','dependency_discovery_isolated','model_load_started','model_load_completed','pair_attempt_reserved'}
        need(events[0]['event']=='calibration_reserved' and one('calibration_reserved')['recipe_sha256']==receipt['recipe_sha256'],'Calibration reservation differs')
        need('DEPENDENCY-POLICY.json' in parsed and _same(parsed['DEPENDENCY-POLICY.json'],DEPENDENCY_POLICY),
             'Missing or changed dependency discovery policy')
        need(_same(one('dependency_discovery_isolated'),dict(policy=DEPENDENCY_POLICY)),
             'Dependency discovery event/policy binding differs')
        need([event['event'] for event in events[:5]]==['calibration_reserved','inputs_admitted','dependency_discovery_isolated','model_load_started','model_load_completed'],
             'Dependency discovery/model-load order differs')
        one('model_load_started');one('model_load_completed')
    need(all(e['event'] in expected_events for e in events),'Unexpected producer event')
    counts=dict(scheduled_claims=len(requests),scheduled_pairs=5*len(requests),completed_claims=len(requests),complete_prediction_claims=0,
        completed_pairs=0,input_unavailable_pairs=0,overlength_pairs=0,unexpected_failed_pairs=0)
    rows=[];expected_files={'recipe.json','MODEL.json','journal.jsonl','events.jsonl'}
    expected_files|={'REPORT.json'} if legacy else {'STATUS.json','RESOURCES.json','io-audit.jsonl','DEPENDENCY-POLICY.json'}
    started=[];reserved=[];committed=[];claim_committed=[];pair_states=[]
    for request in requests:
        cid=request['id'];need(one('claim_started',cid)['input_sha256']==digest(canonical(request)),'Claim input binding')
        pairs=[];evidence={}
        for document in request['documents']:
            did=document['doc_id'];name=f'pairs/{cid}-{did}.json';expected_files.add(name);pair=parsed[name]
            prediction=_native_pair(pair,request,document);pairs.append(pair)
            commit=one('pair_committed',cid,did)
            need(commit['path']==name and commit['sha256']==proofs[name]['sha256'] and commit['status']==pair['status'],'Pair commit binding')
            committed.append((cid,did));counts[{'completed':'completed_pairs','overlength':'overlength_pairs','input_unavailable':'input_unavailable_pairs'}[pair['status']]]+=1
            if document['abstract']:
                started.append((cid,did));one('pair_started',cid,did)
                if not legacy:
                    reserved.append((cid,did));need(one('pair_attempt_reserved',cid,did)['seconds']==recipe['pair_seconds'],'Reserved pair deadline')
            if prediction is not None:
                completed=one('pair_completed',cid,did)
                need(_same(completed['prediction'],prediction) and all(_same(completed.get(k),v) for k,v in pair['observations'].items()),'Native event/measurement differs')
                if prediction['predicted_label']!='NEI':evidence[str(did)]=dict(label=prediction['predicted_label'],sentences=prediction['predicted_rationale'])
            elif pair['status']=='overlength':need(one('pair_failed',cid,did)['error']==pair['reason'],'Overlength event differs')
            else:one('pair_unavailable',cid,did)
            pair_states.append(dict(claim_id=cid,abstract_id=did,state=pair['status'],native_started=bool(document['abstract']),native_returned=prediction is not None,attempt_reserved=bool(document['abstract'])))
        produced=all(p['status']=='completed' for p in pairs);prediction=dict(id=cid,evidence=evidence) if produced else None
        name=f'claims/{cid}.json';expected_files.add(name);claim=parsed[name]
        need(type(claim['id']) is int and claim['id']==cid and claim['condition']==condition and claim['input_sha256']==digest(canonical(request)) and
             claim['status']==('produced' if produced else 'incomplete') and _same(claim['prediction'],prediction),'Claim/native assembly differs')
        need(_same(claim['pairs'],[dict(abstract_id=p['abstract_id'],status=p['status'],path=f'pairs/{cid}-{p["abstract_id"]}.json') for p in pairs]),'Claim pair coverage')
        need(_finite(claim['wall_seconds']) and _finite(claim['cpu_seconds']),'Claim resource accounting')
        commit=one('claim_committed',cid);need(commit['path']==name and commit['sha256']==proofs[name]['sha256'] and commit['status']==claim['status'],'Claim commit binding')
        claim_committed.append(cid);counts['complete_prediction_claims']+=int(produced)
        rows.append(dict(request=request,claim=claim,pairs=pairs,prediction=prediction,produced=produced,proofs=proofs))
    for event,expected in (('pair_started',started),('pair_attempt_reserved',reserved),('pair_committed',committed)):
        if legacy and event=='pair_attempt_reserved':continue
        need([(e['details']['claim_id'],e['details']['abstract_id']) for e in events if e['event']==event]==expected,'Hidden or reordered pair attempts')
    need([e['details']['claim_id'] for e in events if e['event']=='claim_committed']==claim_committed,'Claim commit order differs')
    need(set(raws)==expected_files,'Unexplained producer output files')
    need(one(terminal)['counts']==counts and all(type(v) is int for v in one(terminal)['counts'].values()),'Terminal accounting differs')
    event_counts={name:sum(e['event']==name for e in events) for name in expected_events}
    expected_counts=dict(inputs_admitted=1,claim_started=len(requests),pair_started=len(started),
        pair_completed=counts['completed_pairs'],pair_failed=counts['overlength_pairs'],
        pair_unavailable=counts['input_unavailable_pairs'],pair_committed=5*len(requests),claim_committed=len(requests))
    expected_counts[terminal]=1
    if not legacy:expected_counts.update(calibration_reserved=1,dependency_discovery_isolated=1,model_load_started=1,model_load_completed=1,pair_attempt_reserved=len(reserved))
    need(event_counts==expected_counts,'Orphaned or hidden producer events')
    if legacy:need(parsed['REPORT.json']['counts']==counts and all(type(v) is int for v in parsed['REPORT.json']['counts'].values()) and
                   parsed['REPORT.json']['status']=='schedule_accounted','Legacy report accounting')
    else:
        need(status['counts']==counts and all(type(v) is int for v in status['counts'].values()) and status['pair_states']==pair_states and
             parsed['RESOURCES.json']['counts']==counts and all(type(v) is int for v in parsed['RESOURCES.json']['counts'].values()),'Calibration accounting/state differs')
    return rows,counts,proofs


@dataclass(frozen=True)
class OutcomePartition:
    partition:str
    ids:tuple
    components:Mapping
    rows:tuple
    cases:tuple
    proofs:tuple
    coverage:Mapping
    mapping_fingerprint:str|None


def reconstruct_partition(frame_path,expected_sha256):
    """Read a sealed partition; no outcomes escape until every input rechecks."""
    path=local_path(frame_path);reader=_Capture()
    frame_proof=dict(path=str(path),bytes=path.stat().st_size,sha256=expected_sha256)
    frame=reader.json(frame_proof,1024**2)
    fields={'schema_version','kind','purpose','mode','partition','policy','preparation_transition','expected_ids','producer','code_files','sealed_mapping'}
    need(set(frame)==fields and type(frame['schema_version']) is int and frame['schema_version']==1 and frame['kind']==KIND and
         frame['purpose']=='evaluate' and frame['policy']==POLICY and frame['mode'] in ('production','fictional_qualification') and
         frame['partition'] in ('calibration','dev'),'Explicit evaluator-only frame required')
    partition=frame['partition'];ids=tuple(frame['expected_ids'])
    need(ids and ids==tuple(sorted(set(ids))) and all(type(i) is int and i>0 for i in ids),'Full canonical outcome schedule')
    need(len(ids)==(69 if partition=='calibration' else 300) if frame['mode']=='production' else len(ids)<=8,'Production partition count differs')
    required={Path(__file__).resolve(),ROOT/'experiments/scifact_calibration/calibration.py',ROOT/'experiments/scifact_calibration/inputs.py',ROOT/'experiments/scifact/evaluate.py',ROOT/'experiments/scifact/native_contract.py'}
    pins=frame['code_files'];need(isinstance(pins,list) and len({p['path'] for p in pins})==len(pins) and required<={local_path(p['path']) for p in pins},'Outcome reader/scorer source pins incomplete')
    for proof in pins:reader.read(proof,8*1024**2)
    transition=frame['preparation_transition'];transition_value=reader.json(transition,1024**2)
    mapping_fingerprint=None
    if partition=='dev':
        payload=reader.json(frame['sealed_mapping'],1024**2);mapping_fingerprint=numerical.digest(payload)
        mapping=numerical.mapping_from_payload(payload,expected_fingerprint=mapping_fingerprint)
        need(mapping.training_ids==tuple(transition_value['expected_calibration_ids']), 'Sealed mapping training partition differs')
    else:need(frame['sealed_mapping'] is None,'Calibration cannot depend on an existing map')
    source_frame,manifest,base,original_corpus,originals=_preparation(reader,transition,partition)
    def product(key,kind,purpose):
        spec=manifest['products'][key];need(spec['kind']==kind and purpose in spec['purposes'],'Source product role does not permit evaluator operation')
        permissions={'preparation_audit'}
        if key=='corpus':permissions|={'fit','tune','calibrate','predict','evaluate'}
        elif key!='split':permissions.add(purpose)
        need(set(spec['purposes'])==permissions,'Source product permissions changed')
        name=str(_name(spec['path']));proof=dict(path=str(base/name),bytes=spec['bytes'],sha256=spec['sha256']);raw=reader.read(proof)
        return (_json_lines(raw) if spec['format']=='jsonl' else parse_json(raw)),proof
    corpus_rows,corpus_proof=product('corpus','public_corpus','evaluate');corpus={d['doc_id']:d for d in corpus_rows}
    queries,_=product('queries_'+partition,'query_only','calibrate' if partition=='calibration' else 'predict')
    references,reference_proof=product('references_'+partition,'evaluation_reference','calibrate' if partition=='calibration' else 'evaluate')
    split,_=product('split','preparation_split','preparation_audit')
    need(tuple(r['id'] for r in queries)==tuple(r['id'] for r in references)==tuple(split['partitions'][partition])==ids,'Frozen source partition membership differs')
    need(_same(corpus_rows,original_corpus) and _same(references,[originals[i] for i in ids]) and
         _same(queries,[dict(id=i,claim=originals[i]['claim']) for i in ids]),'Original source projection differs')
    need(split['partitions']['calibration']==source_frame['expected_calibration_ids'] and
         split['counts']==source_frame['expected_partitions'],'Preserved split authority differs')
    components={i:split['group_by_claim'][str(i)] for i in ids}
    if frame['mode']=='production':need(len(set(components.values()))==(49 if partition=='calibration' else 247),'Production component count differs')
    descriptor=frame['producer'];need(set(descriptor)=={'root','receipt','recipe','requests','retrieval','retrieval_format','admission'},'Producer descriptor fields')
    requests=_json_lines(reader.read(descriptor['requests']))
    need(tuple(r['id'] for r in requests)==ids,'Producer request schedule differs')
    retrieval_raw=reader.read(descriptor['retrieval'])
    if descriptor['retrieval_format']=='sc05_bundle':
        retrieval=parse_json(retrieval_raw);need(partition=='calibration' and retrieval['kind']=='sc05_calibration_retrieval_v1' and
            retrieval['purpose']=='calibrate' and retrieval['schedule']==list(ids) and
            _same(retrieval['transition'],transition) and retrieval['classifier_called'] is False and retrieval['fit_performed'] is False and
            retrieval['reference_products_read'] is False,'Calibration retrieval authority differs')
        # Current sealed retrieval keeps source text only in the separately
        # anchored request file. Earlier bundles duplicated those same rows.
        need(_same(retrieval['requests'],requests) if 'requests' in retrieval else
             type(retrieval.get('scheduled_pairs')) is int and retrieval['scheduled_pairs']==5*len(requests),
             'Calibration retrieval/request binding differs')
        if 'scheduled_pairs' in retrieval:
            need(type(retrieval['scheduled_pairs']) is int and retrieval['scheduled_pairs']==5*len(requests),
                 'Calibration retrieval pair accounting differs')
        retrieval=retrieval['retrieval']
    else:
        need(descriptor['retrieval_format']=='jsonl' and partition=='dev','Explicit retained retrieval format');retrieval=_json_lines(retrieval_raw)
    need(tuple(r['id'] for r in retrieval)==ids,'Retrieval schedule differs')
    for request,query,retrieved in zip(requests,queries,retrieval):
        need(set(request)=={'id','claim','documents'} and request['claim']==query['claim'] and type(request['id']) is int and
             len(request['documents'])==len(retrieved['retrieved'])==5,'Query/source projection differs')
        docs=[d['doc_id'] for d in request['documents']];need(len(set(docs))==5 and all(type(i) is int and i in corpus for i in docs),'Five unique corpus documents required')
        for rank,(document,item) in enumerate(zip(request['documents'],retrieved['retrieved']),1):
            need(_same(document,corpus[document['doc_id']]) and set(item)=={'doc_id','rank','score','document_sha256'} and
                 type(item['doc_id']) is int and type(item['rank']) is int and (item['doc_id'],item['rank'])==(document['doc_id'],rank) and
                 type(item['score']) in (int,float) and math.isfinite(item['score']) and
                 item['document_sha256']==digest(canonical(document)),'Retrieval/source binding differs')
    native,counts,proofs=_read_worker(reader,descriptor,requests,partition)
    old_dispositions=None
    if partition=='dev':
        old=descriptor['admission'];need(isinstance(old,dict) and set(old)=={'receipt','dispositions','checks','frame'},'Retained dev admission proof required')
        receipt=reader.json(old['receipt'],8*1024**2);need(receipt.get('status')=='complete','Prior analysis not complete')
        old_frame=reader.json(old['frame'],8*1024**2)
        need(receipt['frame_sha256']==old['frame']['sha256'] and _same(old_frame['references'],reference_proof),'Retained analysis frame/reference binding')
        old_model=reader.json(old_frame['model'],8*1024**2)
        configuration=dict(method='multivers_fever_sci_zero_shot',precision='float32',force_rationale=False,max_tokens=4096,
            retrieval='retained_baseline_top5',label_threshold=None,rationale_threshold=.5,label_order=['CONTRADICT','NEI','SUPPORT'])
        need(old_model['kind']=='sc03_external_pretrained_model' and _same(old_model['configuration'],configuration) and
             old_model['local_fitting_performed'] is False,'Original model/scientific configuration differs')
        old_base=local_path(old['receipt']['path']).parent
        for key,name in (('dispositions','DISPOSITIONS.json'),('checks','CHECKS.json')):
            need(local_path(old[key]['path'])==old_base/name and _same(receipt['files'][name],old[key]),'Retained admission receipt binding')
        old_dispositions=reader.json(old['dispositions']);checks=reader.json(old['checks'])
        need(tuple(r['id'] for r in old_dispositions)==ids,'Retained admission schedule differs')
        check_ids=[r.get('id',r.get('candidate',{}).get('prediction',{}).get('id')) for r in checks]
        need(all(type(i) is int for i in check_ids) and len(set(check_ids))==len(check_ids) and
             set(check_ids)=={record['request']['id'] for record in native if record['produced']},'Missing or duplicate retained admission checks')
        old_checks=dict(zip(check_ids,checks))
    else:need(descriptor['admission'] is None,'Calibration admission must be independently reconstructed')
    from experiments.scifact.evaluate import strict_correct as maintained_strict
    rows=[];cases=[]
    for index,(gold,item) in enumerate(zip(references,native)):
        cid=gold['id'];produced=item['produced'];admitted=produced;prediction=item['prediction']
        if old_dispositions is not None:
            old=old_dispositions[index];need(old['producer_status']==('produced' if produced else 'input_unavailable') and
                _same(old['prediction'],prediction),'Retained primary prediction/producer differs')
            need(old['check_status']==('accepted' if admitted else 'not_run'),'Retained admission disagrees with independent source reconstruction')
            if admitted:
                checked=old_checks[cid];candidate=checked['candidate']
                expected_request=dict(schema_version=1,benchmark_id='scifact',release_sha256=manifest['archive']['sha256'],
                    claim_id=cid,claim_sha256=digest(canonical(queries[index])),corpus_sha256=corpus_proof['sha256'],
                    model_sha256=old_frame['model']['sha256'],configuration_sha256=digest(canonical(configuration)))
                bindings=[dict(doc_id=int(did),sentence_id=i,text_sha256=digest(corpus[int(did)]['abstract'][i].encode()))
                    for did,item in prediction['evidence'].items() for i in item['sentences']]
                envelope=candidate['envelope'];observations=[pair['observations'] for pair in item['pairs']]
                need(candidate['kind']=='accepted_candidate' and candidate['scientific_validation']=='not_performed' and
                     set(envelope)=={'request_sha256','prediction_sha256','retrieved','source_bindings','producer_code_sha256','resources'} and
                     _same(candidate['prediction'],prediction) and _same(candidate['request'],expected_request) and
                     checked['input_sha256']==digest(canonical(item['request'])) and
                     envelope['prediction_sha256']==digest(canonical(prediction)) and
                     envelope['request_sha256']==digest(canonical(expected_request)) and _sentence_bindings(envelope['source_bindings'],bindings) and
                     envelope['producer_code_sha256']==old_model['producer_code']['sha256'] and
                     _same(envelope['retrieved'],retrieval[index]['retrieved']),'Retained native admission binding differs')
                measured=checked['measured_transformer_resources']
                need(measured['input_tokens']==sum(p['token_count'] for p in observations) and measured['generated_output_tokens']==0 and
                     measured['tokenizer_assets_receipt_sha256']==old_model['acquisition_receipt']['sha256'] and
                     measured['mode']=='non_autoregressive_sequence_and_sentence_classification' and
                     _same(measured['pair_observations'],observations),'Retained native measurement binding differs')
                resources=envelope['resources']
                need(resources['wall_seconds']==item['claim']['wall_seconds'] and resources['cpu_seconds']==item['claim']['cpu_seconds'] and
                     resources['input_bytes']==len(canonical(item['request'])) and resources['output_bytes']==len(canonical(item['claim'])) and
                     resources['examples']==1 and resources['provider_cost_usd']==0 and resources['token_usage_reason']=='not_applicable_non_llm' and
                     all(resources[k] is None for k in ('model_input_tokens','model_output_tokens','tokenizer_identity','provider_usage')),
                     'Retained native resources differ')
        success=strict_outcome(gold,prediction,produced=produced,admitted=admitted,corpus=corpus)
        comparison=int(produced and admitted and maintained_strict(gold,prediction))
        need(comparison==success,'Independent strict outcome disagrees with current scorer')
        documents=tuple(d['doc_id'] for d in item['request']['documents'])
        confidence=numerical.extract_confidence(cid,documents,item['pairs'],
            pair_proofs={d:proofs[f'pairs/{cid}-{d}.json'] for d in documents},source_proofs={d:corpus_proof for d in documents})
        need((confidence.status=='available')==produced,'Native/confidence coverage disagreement')
        rows.append(numerical.calibration_row(cid,confidence,produced=produced,admitted=admitted,
            strict_success=success,outcome_proof=reference_proof))
        cases.append(freeze(dict(id=cid,produced=produced,admitted=admitted,strict_success=success,
            strict_scorer_agreement=True,native_assembly_agreement=True,reference_sha256=digest(canonical(gold)),
            request_sha256=digest(canonical(item['request'])),claim_proof=proofs[f'claims/{cid}.json'],
            source_documents=[dict(doc_id=d,document_sha256=digest(canonical(corpus[d])),corpus_proof=corpus_proof) for d in documents],
            confidence_status=confidence.status,confidence_reason=confidence.reason)))
    final_proofs=reader.finish()
    return OutcomePartition(partition,ids,freeze(components),tuple(rows),tuple(cases),final_proofs,
        freeze(dict(scheduled=len(ids),components=len(set(components.values())),produced=sum(r.produced for r in rows),
            admitted=sum(r.admitted for r in rows),available_scores=sum(r.confidence.status=='available' for r in rows),
            missing_scores=sum(r.confidence.status!='available' for r in rows),strict_scorer_agreement=len(rows),
            native_assembly_agreement=len(rows),worker_counts=counts,scientific_scope='Exposed public benchmark; no clinical claim.')),
        mapping_fingerprint)
