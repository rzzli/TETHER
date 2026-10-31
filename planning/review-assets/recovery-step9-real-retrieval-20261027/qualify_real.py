"""Two existing bounded policies over five declared original literature records."""
from datetime import datetime,timezone
import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import sys
import time

from asof.atomic import publish_bytes
from asof.serde import canonical,encode,fingerprint,parse_json
from asof.study.source_preparation import prepare_source_request
from asof.study.retrieval_preparation import prepare_retrieval,verify_retrieval_preparation,policy_for

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
RAW=Path(r'E:\projects_data\drug_target_agents_data')
protocol=parse_json((HERE/'PROTOCOL-v1.json').read_bytes())
authority_raw=(HERE/'SOURCE-AUTHORITY-v1.json').read_bytes()
source_authority=parse_json(authority_raw)
assert hashlib.sha256(authority_raw).hexdigest()==protocol['source_authority_sha256']
assert metadata.version('asof-target-agents')=='0.3.6' and metadata.version('pyarrow')=='21.0.0'
assert not (HERE/'QUALIFICATION.json').exists() and not (HERE/'FAILURE.json').exists()
roots=dict(project=ROOT,raw=RAW)
allowed={os.path.normcase(str(roots[p['root_id']].joinpath(*p['relative_path'].split('/'))))
         for p in source_authority['files'].values()}
out=ROOT/'data/cache'/('r09-real-multirecord-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
out.mkdir(exist_ok=False)
state=dict(schema_version=1,status='running',output=str(out),version='0.3.6',pyarrow_version='21.0.0',
    source_authority_sha256=protocol['source_authority_sha256'],guards=dict(unapproved_source=[],dispatch=[]),
    real_universe_expanded_within_existing_case=True,fresh_case=False,new_downloads=0,model_calls=0,
    tokenizer_calls=0,provider_spend_usd=0,scientific_validation='not_attempted')


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def audit(event,args):
    if event in ('subprocess.Popen','os.system','socket.connect','socket.getaddrinfo'):
        state['guards']['dispatch'].append(event)
        raise RuntimeError('No network/model/tokenizer/other child in real retrieval preparation')
    if event=='open' and args and isinstance(args[0],(str,bytes,os.PathLike)):
        path=os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if any(p.casefold() in ('benchmark','gold_evidence','adjudication','completed-responses') for p in Path(path).parts):
            raise RuntimeError('Evaluation/human answer trees excluded')
        if path.startswith('e:'):
            mode=args[1] if len(args)>1 else None
            flags=args[2] if len(args)>2 and isinstance(args[2],int) else 0
            if path not in allowed or flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND) or (isinstance(mode,str) and any(c in mode for c in 'wax+')):
                state['guards']['unapproved_source'].append(path)
                raise RuntimeError('Only the original approved source files may be read on E')


sys.addaudithook(audit)
started=time.monotonic()
deadline=started+protocol['preparation_seconds_limit']
try:
    pins=parse_json((ROOT/protocol['source_pins_path']).read_bytes())['source_pins']
    assert all(sha(ROOT/n)==h for n,h in pins.items())
    publish_bytes(out/'protocol.json',canonical(protocol))
    parent=prepare_source_request(HERE/'SOURCE-AUTHORITY-v1.json',protocol['source_authority_sha256'],
        roots,out/'source',deadline=deadline)
    request=parse_json((out/'source/request.json').read_bytes())
    rows=request['source_request']['evidence']
    coverage=request['source_request']['coverage']
    assert len(rows)==5 and sorted(r['observation_id'] for r in rows)==protocol['candidate_ids']
    assert coverage['observations_available']==9 and coverage['missing_input_count']==65
    assert all(r['scientific_record']['category']=='literature' and not r['scientific_record']['features'] for r in rows)
    raw_audit=parse_json((out/'source/source-audit.json').read_bytes())
    assert len(raw_audit['selected_rows'])==5 and all(r['whole_record_equal'] for r in raw_audit['selected_rows'])
    retrieval_authority=dict(schema_version=1,kind='real_source_preparation',
        parent=dict(root_id='project',relative_path=(out/'source').relative_to(ROOT).as_posix()),
        parent_receipt_sha256=parent['receipt_sha256'],source_authority_sha256=protocol['source_authority_sha256'],
        candidate_ids=protocol['candidate_ids'],category='literature',request_sha256=fingerprint(request),
        grounded_fingerprints={r['observation_id']:r['admitted_sha256'] for r in rows})
    anchor=fingerprint(retrieval_authority)
    publish_bytes(out/'retrieval-authority.json',canonical(retrieval_authority))
    results=[]
    for strategy in protocol['strategies']:
        policy=policy_for(strategy)
        assert policy['max_records']==2 and policy['max_request_bytes']==12000
        result=prepare_retrieval(retrieval_authority,anchor,policy,out/strategy,roots=roots,deadline=deadline)
        selected_request=parse_json((out/strategy/'request.json').read_bytes())
        selected_rows=[] if selected_request is None else selected_request['source_request']['evidence']
        originals={r['observation_id']:r for r in rows}
        assert all(canonical(r)==canonical(originals[r['observation_id']]) for r in selected_rows)
        assert result['coverage']['declared_candidates']==result['coverage']['raw_qualified_candidates']==5
        assert result['coverage']['parent_observations_available']==9 and result['coverage']['missing_input_count']==65
        assert result['coverage']['absence_claim'] is False
        results.append(dict(strategy=strategy,result=encode(result)))
    preparation_seconds=time.monotonic()-started
    assert preparation_seconds<300
    replay_start=time.monotonic()
    for row in results:
        row['replay']=encode(verify_retrieval_preparation(out/row['strategy'],row['result']['receipt_sha256'],
            anchor,roots=roots,deadline=replay_start+protocol['replay_seconds_limit']))
    assert not any(state['guards'].values()) and all(sha(ROOT/n)==h for n,h in pins.items())
    state.update(status='five_original_record_bounded_retrieval_verified',
        source_parent_receipt_sha256=parent['receipt_sha256'],source_request_sha256=fingerprint(request),
        retrieval_authority_sha256=anchor,declared_candidates=5,raw_rows_equal=5,
        parent_observations_available=9,missing_input_count=65,results=results,
        preparation_seconds=preparation_seconds,replay_seconds=time.monotonic()-replay_start,
        candidate_scientific_record_bytes={r['observation_id']:len(canonical(r['scientific_record'])) for r in rows},
        source_pins_unchanged=True,nontrivial_real_candidate_universe=True,
        relevance_or_scientific_performance_validated=False)
    publish_bytes(out/'qualification.json',canonical(state))
    with (HERE/'QUALIFICATION.json').open('x',encoding='utf-8') as stream:
        json.dump(state,stream,indent=2)
    print(json.dumps(dict(status=state['status'],output=str(out),preparation_seconds=preparation_seconds,
        replay_seconds=state['replay_seconds'],selection_counts=[r['result']['coverage']['selected_count'] for r in results])))
except BaseException as error:
    state.update(status='failed',error_class=type(error).__name__,message=str(error),elapsed_seconds=time.monotonic()-started)
    publish_bytes(out/'failure.json',canonical(state))
    with (HERE/'FAILURE.json').open('x',encoding='utf-8') as stream:
        json.dump(state,stream,indent=2)
    raise
