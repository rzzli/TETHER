"""Exact original L/O execution projection, never evaluator-package promotion.

This is a role projection after coordinator acceptance, not a replacement for
independent native/source replay. Only fixed original execution locations are
opened. Acquisition bytes are reconstructed again; evaluator outputs are not
used to reconstruct the candidates. Activation bytes stay coordinator-only.
"""
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
import base64
import stat

from tether_engine.atomic import publish_bytes
from tether_engine.journal import read_chain
from tether_engine.serde import Frozen, canonical, encode, fingerprint, freeze, parse_json, safe_child
from experiments.labbench.native_contract import validate_query
from experiments.litqa_comparison import acquisition, codecs
from . import contracts

KIND='sc05_original_execution_v1'


def _path(value):
    contracts.need(isinstance(value,str) and Path(value).is_absolute(), 'Absolute original path required')
    path=Path(value)
    contracts.need('..' not in path.parts, 'Noncanonical original path')
    for item in (path,*path.parents):
        if item.exists():
            info=item.lstat()
            contracts.need(not item.is_symlink() and not getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT,
                           'Linked original path forbidden')
    return path


def _proof(value):
    contracts.need(isinstance(value,Mapping) and set(value)=={'path','sha256','bytes'}, 'Exact file proof required')
    _path(value['path']);contracts.digest(value['sha256'])
    contracts.need(type(value['bytes']) is int and 0<=value['bytes']<=128*1024**2,'File proof byte bound')
    return value


class _Reader:
    def __init__(self):self.proofs={}

    def read(self,path,expected=None,role='original_execution_control'):
        path=_path(str(path));before=path.stat()
        contracts.need(path.is_file() and before.st_size<=128*1024**2,'Original file bound')
        raw=path.read_bytes();after=path.stat()
        contracts.need((before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),
                       'Original input changed during read')
        proof=dict(path=str(path),sha256=codecs.digest(raw),bytes=len(raw))
        if isinstance(expected,str):contracts.need(proof['sha256']==expected,'Original external anchor mismatch')
        elif expected is not None:contracts.need(canonical(proof)==canonical(_proof(expected)),'Original file proof mismatch')
        prior=self.proofs.get(str(path))
        contracts.need(prior is None or prior['proof']==proof,'Original file changed across reads')
        self.proofs[str(path)]=dict(role=role,proof=proof)
        return raw

    def json(self,path,expected=None,role='original_execution_control'):
        return parse_json(self.read(path,expected,role))

    def recheck(self):
        for row in tuple(self.proofs.values()):self.read(row['proof']['path'],row['proof'],row['role'])


def _descriptor(value):
    contracts.need(isinstance(value,Mapping) and set(value)=={'kind','role','root','root_receipt_sha256'}, 'Original execution descriptor fields')
    contracts.need(value['kind']==KIND and value['role']=='original_sc04_execution','Evaluator/annotated parents are forbidden')
    _path(value['root']);contracts.digest(value['root_receipt_sha256'])
    return freeze(value)


def _package(reader,root,phase,descriptor,frame_sha):
    phase_root=root/phase
    contracts.need(set(descriptor)=={'root','package_sha256','stage_receipt_sha256'} and
                   _path(descriptor['root'])==phase_root,'Original phase location differs')
    package=reader.json(phase_root/'PACKAGE-RECEIPT.json',descriptor['package_sha256'])
    contracts.need(package.get('status')=='complete' and package.get('phase')==phase and package.get('frame_sha256')==frame_sha,
                   'Original phase package identity')
    files=package['files']
    contracts.need(isinstance(files,dict) and all(isinstance(n,str) for n in files),'Original phase inventory')
    for name,proof in files.items():
        contracts.need(Path(_proof(proof)['path'])==safe_child(phase_root,name),'Original phase member location')
        contracts.need(Path(name).name not in ('FAILURE.json','FINALIZATION-FAILED.json','DEADLINE.json'),'Failed original package')
    stage=phase_root/'worker/phase'
    stage_name='worker/phase/STAGE-RECEIPT.json'
    contracts.need(stage_name in files and files[stage_name]['sha256']==descriptor['stage_receipt_sha256'],'Original stage anchor')
    receipt=reader.json(stage/'STAGE-RECEIPT.json',files[stage_name])
    contracts.need(receipt.get('status')=='complete','Incomplete original stage')
    for name,proof in receipt['files'].items():
        entry=files.get('worker/phase/'+name)
        contracts.need(entry is not None and proof=={k:entry[k] for k in ('sha256','bytes')},'Original stage/package member join')
    def read(name,role='original_execution_control'):
        path=safe_child(stage,name)
        contracts.need(name in receipt['files'],'Unlisted original stage read')
        return reader.json(path,files['worker/phase/'+name],role)
    return stage,receipt,files,read


def _reconstruct(descriptor,expected_schedule=None):
    descriptor=_descriptor(descriptor);root=_path(descriptor['root']);reader=_Reader()
    receipt=reader.json(root/'ROOT-RECEIPT.json',descriptor['root_receipt_sha256'])
    contracts.need(receipt.get('status')=='primary_execution_complete','Only original primary execution is eligible')
    root_files=receipt['files']
    names={'FRAME.json','COMPLETE.json','journal.jsonl','expand-ANCHOR.json','collect-ANCHOR.json','rank-ANCHOR.json','answer-ANCHOR.json'}
    contracts.need(set(root_files)==names,'Original primary root inventory')
    for name,proof in root_files.items():contracts.need(Path(_proof(proof)['path'])==root/name,'Original root proof location')
    frame=reader.json(root/'FRAME.json',root_files['FRAME.json'])
    contracts.need(frame.get('kind')=='sc04_primary_execution_v1' and frame.get('purpose') in ('production','fictional_qualification'),
                   'Evaluator/diagnostic frame cannot supply baseline')
    contracts.need(receipt['frame_sha256']==root_files['FRAME.json']['sha256'],'Original frame anchor')
    count=199 if frame['purpose']=='production' else 2
    ids=frame['schedule']
    contracts.need(frame['count']==len(ids)==count and len(set(ids))==count,'Complete original baseline schedule')
    if expected_schedule is not None:contracts.need(tuple(ids)==tuple(expected_schedule),'Expected baseline schedule differs')
    contracts.need(set(frame['query_products'])=={'answer_queries','source_queries'},'Original query role inventory')
    query_proof=_proof(frame['query_products']['answer_queries'])
    queries=reader.json(query_proof['path'],query_proof,'visible_query')
    queries=tuple(validate_query(q) for q in queries)
    contracts.need([q['id'] for q in queries]==ids,'Original query identity/order')
    complete=reader.json(root/'COMPLETE.json',root_files['COMPLETE.json'])
    contracts.need(complete.get('status')=='primary_execution_complete' and complete.get('purpose')==frame['purpose']
        and complete.get('scientific_scoring_performed') is False and complete.get('provider_cost_usd')==0
        and set(complete['phases'])=={'expand','collect','rank','answer'},'Original completion scope')
    stages={}
    for phase in ('collect','answer'):
        anchor=reader.json(root/(phase+'-ANCHOR.json'),root_files[phase+'-ANCHOR.json'])
        contracts.need(anchor==complete['phases'][phase],'Original phase root anchor join')
        stages[phase]=_package(reader,root,phase,anchor,receipt['frame_sha256'])
        config=stages[phase][3]('CONFIG.json')
        contracts.need(config['stage']==phase and config['ids']==ids,'Original phase schedule')
    cases=[]
    for i,query in enumerate(queries):
        collect_root,collect_receipt,collect_files,collect_read=stages['collect']
        answer_root,answer_receipt,answer_files,answer_read=stages['answer']
        collect=collect_read(f'slots/{2*i:04d}.json')
        answer=answer_read(f'slots/{4*i:04d}.json')
        for row,branch,ordinal in ((collect,'L',2*i),(answer,'L/O',4*i)):
            contracts.need(row['id']==query['id'] and row['branch']==branch and row['ordinal']==ordinal and row['status']=='completed',
                           'Fixed original L/O slot identity')
        source=collect['product'];source_root=collect_root/'products'/f'{2*i:04d}'
        contracts.need(Path(source['root'])==source_root and source['plan']['strategy']=='lexical'
            and source['plan']['question']=={'id':query['id'],'question':query['question']},'Original lexical source identity')
        source_receipt=reader.json(source_root/'RECEIPT.json',source['receipt'],'raw_source_receipt')
        contracts.need(source['receipt']['sha256']==collect_receipt['files'][f'products/{2*i:04d}/RECEIPT.json']['sha256'],
                       'Original source/stage receipt join')
        source_proofs=[]
        for name,proof in source_receipt['files'].items():
            member=f'products/{2*i:04d}/'+name
            contracts.need(member in collect_receipt['files'] and proof==collect_receipt['files'][member], 'Original source byte membership')
            full=collect_files['worker/phase/'+member]
            reader.read(safe_child(source_root,name),full,'raw_source_parent')
            source_proofs.append(dict(role='raw_source_parent',proof=full))
        manifest=acquisition.verify(source_root,source['receipt']['sha256'],source['plan'])
        selected=codecs.select_order(manifest['pool']['pool'],[p['rank_id'] for p in manifest['pool']['pool']])
        cell=answer_root/'products'/f'{4*i:04d}';prefix=f'products/{4*i:04d}/'
        inp=answer_read(prefix+'INPUT.json','generated_candidate_control')
        contracts.need(set(inp)=={'task','query','items'} and inp['task']=='answer' and inp['query']==encode(query)
                       and canonical(inp['items'])==canonical(selected['sources']),'Original answer/input/selection join')
        context=answer_read(prefix+'CONTEXT.json','original_source_context')
        contracts.need(set(context)=={'policy_kind','query_sha256','source_receipt_sha256','query_plan_sha256',
            'cutoff','catalog_sha256','publications','source_proofs','sources_sha256','bindings','order',
            'request_sha256','coverage','selection','semantic_support','lineage_scope'} and
            context['policy_kind']=='sc04_source_backed_v1' and context['semantic_support']=='unevaluated',
            'Original context cannot contain evaluator annotations')
        contracts.need(context['query_plan_sha256']==fingerprint(source['plan']) and
            context['cutoff']==complete['source_cutoff'] and canonical(context['coverage'])==canonical(manifest['coverage'])
            and canonical(context['selection'])==canonical(selected),'Original source context reconstruction')
        summary=answer_read(prefix+'SUMMARY.json','generated_candidate_control')
        product=answer['product'];disposition=product['disposition']
        contracts.need(set(disposition)=={'id','producer_status','check_status','prediction','reason'} and disposition['id']==query['id'],
                       'Original disposition fields')
        contracts.need(context['query_sha256']==fingerprint(query) and context['sources_sha256']==fingerprint(selected['sources'])
            and context['source_receipt_sha256']==source['receipt']['sha256'] and
            product['collection_receipt_sha256']==source['receipt']['sha256'] and
            tuple(product['order'])==tuple(p['rank_id'] for p in manifest['pool']['pool']),'Original context/source identity')
        contracts.need(summary['task']=='answer' and summary['query_sha256']==fingerprint(query)
            and summary['items_sha256']==fingerprint(selected['sources']) and product['call']['summary']==summary,
            'Original native summary/input join')
        contracts.need(canonical(product['context'])==canonical(answer_files['worker/phase/'+prefix+'CONTEXT.json'])
            and canonical(product['call']['summary_proof'])==canonical(answer_files['worker/phase/'+prefix+'SUMMARY.json']),
            'Original product proof identity')
        native_sha=None;generated_at=None
        native_proofs=[]
        for name,proof in answer_receipt['files'].items():
            if name.startswith(prefix) and (name.endswith('journal.jsonl') or name.startswith(prefix+'native/')):
                full=answer_files['worker/phase/'+name]
                reader.read(safe_child(answer_root,name),full,'generated_candidate_control')
                native_proofs.append(dict(role='generated_candidate_control',proof=full))
        if summary['generation_entered']:
            native_name=prefix+'native/native-response.bin'
            contracts.need(native_name in answer_receipt['files'],'Generated original lacks raw native response')
            native_sha=answer_receipt['files'][native_name]['sha256']
            events=read_chain(cell/'journal.jsonl')
            contracts.utc(events[0]['details']['created_at_utc'])
            wrapper=answer_read(native_name,'generated_candidate_control')
            request=answer_read(prefix+'native/request.json','generated_candidate_control')
            payload=answer_read(prefix+'native/payload.json','generated_candidate_control')
            contracts.need(request['query']==encode(query) and canonical(request['sources'])==canonical(selected['sources'])
                and fingerprint(request)==summary['request_sha256']==context['request_sha256']
                and wrapper['request_sha256']==fingerprint(request) and wrapper['payload_sha256']==fingerprint(payload)
                and request['payload_sha256']==fingerprint(payload),'Original request/native context join')
            body=base64.b64decode(wrapper['body_base64'],validate=True)
            contracts.need(codecs.digest(body)==wrapper['body_sha256'] and wrapper['complete'] is True,'Original native response bytes')
            raw_answer=parse_json(body)['content'].encode('utf-8')
            from experiments.labbench.native_contract import parse_prediction
            try:decoded=parse_prediction(raw_answer,query,[s['source_id'] for s in selected['sources']])
            except ValueError:decoded=None
            contracts.need(canonical(decoded)==canonical(summary['decoded']),'Original native candidate decoding')
        else:contracts.need(summary['status']=='capacity' and summary['decoded'] is None,'Original nongeneration disposition')
        expected_status={'completed':'produced','codec_failure':'parse_failure','capacity':'input_unavailable'}
        contracts.need(summary['status'] in expected_status and disposition['producer_status']==expected_status[summary['status']]
            and canonical(disposition['prediction'])==canonical(summary['decoded']),'Original producer disposition join')
        candidate=contracts.candidate(query,disposition['prediction'],producer_status=disposition['producer_status'],
            original_admission_status=disposition['check_status'],native_call_sha256=native_sha,
            generated_at_utc=generated_at,offered_ids=[s['source_id'] for s in selected['sources']])
        if candidate['prediction'] is not None:
            from experiments.labbench.native_contract import visible_unsure_index
            accepted=(candidate['prediction']['answer_index']==visible_unsure_index(query) or bool(candidate['prediction']['evidence_ids']))
            contracts.need(disposition['check_status']==('accepted' if accepted else 'rejected') and
                isinstance(product['decision'],Mapping) and product['decision']['accepted'] is accepted,
                'Original provenance admission decision differs')
        else:contracts.need(product['decision'] is None,'Unavailable original cannot have admission')
        cases.append(dict(id=query['id'],query=query,candidate=candidate,original_selected_sources=selected['sources'],
            original_collection=dict(root=str(source_root),receipt_sha256=source['receipt']['sha256'],plan=source['plan'],sources=manifest['sources']),
            original_context=context,source_proofs=source_proofs,native_proofs=native_proofs,
            original_disposition=disposition,source_cutoff=complete['source_cutoff'],
            generation_time_unknown_reason='Archived execution has no exact generation timestamp',
            source_validation='reconstructed from original acquisition bytes',native_validation='coordinator accepted replay prerequisite'))
    reader.recheck()
    return freeze(dict(kind='tether_baseline_projection_v1',execution_descriptor=descriptor,purpose=frame['purpose'],
        schedule=ids,queries=queries,cases=cases,original_frame_sha256=receipt['frame_sha256'],
        role_files=list(reader.proofs.values()),scientific_correctness='not_read',
        scope='Original L/O role projection; independent accepted execution is a coordinator prerequisite'))


@dataclass(frozen=True)
class PreparedBaseline(Frozen):
    root: str
    receipt_sha256: str
    manifest: Mapping

    @property
    def queries(self):return self.manifest['queries']
    @property
    def cases(self):return self.manifest['cases']


def prepare_baseline(execution_descriptor,coordinator_acceptance,output):
    _descriptor(execution_descriptor);_proof(coordinator_acceptance)
    output=Path(output).absolute();output.mkdir(parents=True,exist_ok=False)
    # Only this coordinator operation hashes activation bytes. It never parses
    # their scientific content or places them in worker source/control ancestry.
    activation_reader=_Reader()
    activation_reader.read(coordinator_acceptance['path'],coordinator_acceptance,'coordinator_activation_only')
    manifest=_reconstruct(execution_descriptor)
    publish_bytes(output/'COORDINATOR.json',canonical(dict(acceptance=coordinator_acceptance,role='coordinator_activation_only')))
    publish_bytes(output/'BASELINE.json',canonical(manifest))
    files={}
    for i,case in enumerate(manifest['cases']):
        for name,value in (('QUERY',case['query']),('CANDIDATE',case['candidate']),('SOURCES',case['original_selected_sources'])):
            rel=f'cases/{i:04d}/{name}.json';raw=canonical(value)
            publish_bytes(output/rel,raw);files[rel]=dict(sha256=codecs.digest(raw),bytes=len(raw))
    raw=canonical(manifest);files['BASELINE.json']=dict(sha256=codecs.digest(raw),bytes=len(raw))
    receipt=dict(kind='tether_baseline_projection_receipt_v1',files=files,
                 execution_descriptor=execution_descriptor,coordinator_activation_excluded=True)
    publish_bytes(output/'RECEIPT.json',canonical(receipt))
    return PreparedBaseline(str(output),fingerprint(receipt),manifest)


def verify_baseline_projection(descriptor,expected_schedule):
    contracts.need(isinstance(descriptor,Mapping) and set(descriptor)=={'root','receipt_sha256'},'Baseline projection descriptor')
    root=_path(descriptor['root']);reader=_Reader()
    receipt=reader.json(root/'RECEIPT.json',descriptor['receipt_sha256'])
    contracts.need(receipt.get('kind')=='tether_baseline_projection_receipt_v1' and receipt.get('coordinator_activation_excluded') is True,
                   'Baseline projection receipt role')
    contracts.need('COORDINATOR.json' not in receipt['files'],'Coordinator activation cannot be a worker parent')
    rebuilt=_reconstruct(receipt['execution_descriptor'],expected_schedule)
    expected={'BASELINE.json':canonical(rebuilt)}
    for i,case in enumerate(rebuilt['cases']):
        for name,value in (('QUERY',case['query']),('CANDIDATE',case['candidate']),('SOURCES',case['original_selected_sources'])):
            expected[f'cases/{i:04d}/{name}.json']=canonical(value)
    contracts.need(set(receipt['files'])==set(expected),'Exact baseline projection file roles')
    for name,raw in expected.items():
        proof=receipt['files'][name]
        contracts.need(proof==dict(sha256=codecs.digest(raw),bytes=len(raw)),'Baseline projection reconstruction')
        reader.read(safe_child(root,name),dict(path=str(safe_child(root,name)),**proof),'projected_worker_input')
    reader.recheck()
    return PreparedBaseline(str(root),descriptor['receipt_sha256'],rebuilt)


def worker_files(prepared,query_id):
    contracts.need(isinstance(prepared,PreparedBaseline),'Prepared baseline required')
    ids=prepared.manifest['schedule'];contracts.need(query_id in ids,'Unknown baseline query')
    index=ids.index(query_id)
    # Model workers receive only these typed minimal files. Full raw receipts,
    # baseline metadata and activation are for separate coordinator/admission.
    return freeze({name.lower():str(Path(prepared.root)/f'cases/{index:04d}/{name}.json')
                   for name in ('QUERY','CANDIDATE','SOURCES')})
