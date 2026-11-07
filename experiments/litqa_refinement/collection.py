"""One bounded refinement acquisition through the existing SC04 downloader.

Critic-derived terms are control provenance, never scientific source nodes.
The minimal plan contains neither answer choices nor generated criticism.
"""
from collections.abc import Mapping
from pathlib import Path
import time

from tether_engine.atomic import publish_bytes
from tether_engine.journal import RunJournal,read_chain
from tether_engine.serde import canonical,encode,freeze,parse_json,safe_child
from tether_engine.study.stable_read import checked_path,deadline_check,hash_file,read_file,stable_files
from experiments.litqa_comparison import acquisition,codecs
from . import contracts

KIND='tether_refinement_query_plan_v1'
CONTROL_FIELDS={'query_sha256','candidate_sha256','source_context_sha256',
                'critic_context_sha256','critic_native_call_sha256','is_scientific_evidence'}


def plan(question,terms,control,*,policy=acquisition.legacy.DEFAULT_POLICY):
    question=codecs.question_view(question);terms=contracts.query_terms(terms)
    contracts.need(isinstance(control,Mapping) and set(control)==CONTROL_FIELDS and
                   control['is_scientific_evidence'] is False,'Query control provenance fields')
    for key in CONTROL_FIELDS-{'is_scientific_evidence'}:contracts.digest(control[key],key)
    native=acquisition.plan(question,'expanded',policy=policy,expansion=dict(queries=terms))
    return freeze(dict(kind=KIND,question=question,terms=terms,control_provenance=control,
        raw_plan=native,selection_scope='option_and_candidate_informed_generated_terms',
        scientific_parents='original_public_metadata_and_fulltext_responses_only'))


def from_critic(query,prior,critique,original_selected_sources,*,policy=acquisition.legacy.DEFAULT_POLICY):
    query,sources=contracts.raw_sources(query,original_selected_sources)
    prior=contracts.validate_candidate(query,prior,[s['source_id'] for s in sources])
    critique=contracts.validate_critique(query,prior,critique,sources)
    if critique['decoded'] is None:
        return freeze(dict(status='unavailable',reason='refinement_query_unavailable',
            cause='critic_'+critique['native_status'],plan=None,critic_context_sha256=codecs.digest(canonical(critique))))
    control=dict(query_sha256=critique['query_sha256'],candidate_sha256=critique['candidate_sha256'],
        source_context_sha256=critique['source_context_sha256'],critic_context_sha256=codecs.digest(canonical(critique)),
        critic_native_call_sha256=critique['native_call_sha256'],is_scientific_evidence=False)
    value=plan(dict(id=query['id'],question=query['question']),critique['decoded']['queries'],control,policy=policy)
    return freeze(dict(status='available',reason=None,cause=None,plan=value,
                       critic_context_sha256=codecs.digest(canonical(critique))))


def validate_plan(value):
    contracts.need(isinstance(value,Mapping) and set(value)=={'kind','question','terms','control_provenance',
        'raw_plan','selection_scope','scientific_parents'},'Exact minimal refinement plan required')
    rebuilt=plan(value['question'],value['terms'],value['control_provenance'],policy=value['raw_plan']['policy'])
    contracts.need(canonical(value)==canonical(rebuilt),'Refinement plan reconstruction differs')
    return rebuilt


def _end(deadline,seconds=120):
    end=time.monotonic()+seconds if deadline is None else deadline
    deadline_check(end);return end


def _proof(path,end):
    path=Path(path).absolute()
    return freeze(dict(path=str(path),**hash_file(path,end)))


def _inventory(root,end):
    result={}
    for path in sorted(root.rglob('*')):
        deadline_check(end)
        if path.is_dir():continue
        relative=path.relative_to(root).as_posix();checked_path(root,relative)
        if relative=='RECEIPT.json':continue
        contracts.need(len(result)<64,'Refinement acquisition file bound')
        result[relative]=hash_file(path,end)
    return freeze(result)


def _manifest(value,raw_root,raw_manifest,raw_receipt):
    return freeze(dict(kind='tether_refinement_collection_v1',plan=value,
        raw_collection=dict(root=str(raw_root),receipt_sha256=raw_receipt['sha256'],plan=value['raw_plan']),
        raw_manifest_sha256=codecs.digest(canonical(raw_manifest)),
        coverage=raw_manifest['coverage'],accounting=raw_manifest['accounting'],
        request_count=len(raw_manifest['requests']),
        control_provenance=value['control_provenance'],control_is_scientific_evidence=False))


def acquire(value,output,*,deadline):
    value=validate_plan(value);end=_end(deadline)
    journal=RunJournal(Path(output),kind='build');root=journal.output
    try:
        publish_bytes(root/'PLAN.json',canonical(value))
        journal.append('refinement_plan_bound',plan_sha256=codecs.digest(canonical(value)))
        # Exactly one reuse of the existing two-search/three-article engine.
        raw=acquisition.acquire(value['raw_plan'],root/'raw',deadline=end)
        raw_receipt=_proof(root/'raw/RECEIPT.json',end)
        acquisition.verify(root/'raw',raw_receipt['sha256'],value['raw_plan'])
        manifest=_manifest(value,root/'raw',raw,raw_receipt)
        publish_bytes(root/'MANIFEST.json',canonical(manifest))
        journal.append('refinement_collection_completed',manifest_sha256=codecs.digest(canonical(manifest)),
                       raw_receipt_sha256=raw_receipt['sha256'])
        journal.close();deadline_check(end)
        publish_bytes(root/'RECEIPT.json',canonical(dict(kind='tether_refinement_collection_receipt_v1',status='complete',
            files=_inventory(root,end),plan_sha256=codecs.digest(canonical(value)))))
        deadline_check(end);return manifest
    except BaseException as error:
        try:journal.fail(error,'refinement_collection')
        except BaseException:pass
        publish_bytes(root/'FAILURE.json',canonical(dict(error_type=type(error).__name__,automatic_retry=False)))
        raise
    finally:journal.close()


def verify(root,receipt_sha256,expected_plan,*,deadline=None):
    value=validate_plan(expected_plan);end=_end(deadline);root=Path(root).absolute()
    receipt_path=checked_path(root,'RECEIPT.json')
    with stable_files((receipt_path,),deadline=end):
        raw=read_file(receipt_path,end,1024**2)
        contracts.need(codecs.digest(raw)==receipt_sha256,'Refinement collection external anchor')
        receipt=parse_json(raw)
        contracts.need(set(receipt)=={'kind','status','files','plan_sha256'} and receipt['kind']=='tether_refinement_collection_receipt_v1'
            and receipt['status']=='complete' and receipt['plan_sha256']==codecs.digest(canonical(value)),
            'Refinement collection receipt identity')
        paths=tuple(checked_path(root,name) for name in receipt['files'])
        with stable_files(paths,deadline=end):
            contracts.need(canonical(_inventory(root,end))==canonical(receipt['files']),'Exact refinement wrapper inventory')
            contracts.need('FAILURE.json' not in receipt['files'],'Failed refinement cannot be resumed')
            contracts.need(parse_json(read_file(root/'PLAN.json',end,1024**2))==encode(value),'Refinement plan identity')
            raw_receipt=_proof(root/'raw/RECEIPT.json',end)
            source=acquisition.verify(root/'raw',raw_receipt['sha256'],value['raw_plan'])
            expected=_manifest(value,root/'raw',source,raw_receipt)
            manifest=parse_json(read_file(root/'MANIFEST.json',end,32*1024**2))
            contracts.need(canonical(manifest)==canonical(expected),'Refinement collection reconstruction')
            events=read_chain(root/'journal.jsonl')
            contracts.need([e['event'] for e in events]==['build_reserved','refinement_plan_bound','refinement_collection_completed']
                and events[1]['details']==dict(plan_sha256=codecs.digest(canonical(value)))
                and events[2]['details']==dict(manifest_sha256=codecs.digest(canonical(expected)),raw_receipt_sha256=raw_receipt['sha256']),
                'Refinement collection journal binding')
            deadline_check(end)
            return expected
