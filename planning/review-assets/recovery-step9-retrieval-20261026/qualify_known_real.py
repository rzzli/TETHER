"""Same exposed single-record scope, current parent, unchanged policies, no model."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time
from asof.atomic import publish_bytes
from asof.serde import canonical, encode, fingerprint, parse_json
from asof.study.source_preparation import prepare_source_request
from asof.study.retrieval_preparation import prepare_retrieval, verify_retrieval_preparation, policy_for

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
SOURCE = HERE.parent/'recovery-step9-token-aware-20261026'
RAW = Path(r'E:\projects_data\drug_target_agents_data')
protocol = parse_json((HERE/'KNOWN-REAL-PROTOCOL.json').read_bytes())
source_authority = parse_json((SOURCE/'SOURCE-AUTHORITY-v1.json').read_bytes())
roots = {'project': ROOT, 'raw': RAW}
allowed = {os.path.normcase(str(roots[p['root_id']].joinpath(*p['relative_path'].split('/'))))
           for p in source_authority['files'].values()}
OUT = ROOT/'data/cache'/('r09-retrieval-known-real-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
OUT.mkdir(exist_ok=False)
state = dict(schema_version=1, status='running', output=str(OUT), guards=dict(original_data=[],dispatch=[]),
             model_calls=0, tokenizer_calls=0, real_universe_expansion=False, scientific_validation='not_performed')


def audit(event,args):
    if event == 'open' and args and isinstance(args[0], (str,bytes,os.PathLike)):
        path = os.path.normcase(os.path.abspath(os.fsdecode(args[0])))
        if path.startswith(os.path.normcase('E:\\')) and path not in allowed:
            state['guards']['original_data'].append(path)
            raise PermissionError('Original data outside previously approved one-case scope')
        if any(p.lower() in ('benchmark','gold_evidence','adjudication','completed-responses') for p in Path(path).parts):
            raise PermissionError('Protected evaluation payload unavailable')
    if event in ('subprocess.Popen','socket.connect'):
        state['guards']['dispatch'].append(event)
        raise PermissionError('No model, tokenizer, network or archived-verifier process')


sys.addaudithook(audit)
started = time.monotonic()
deadline = started+300
try:
    publish_bytes(OUT/'protocol.json',canonical(protocol))
    parent = prepare_source_request(SOURCE/'SOURCE-AUTHORITY-v1.json',protocol['source_authority_sha256'],
                                    roots,OUT/'source',deadline=deadline)
    request = parse_json((OUT/'source/request.json').read_bytes())
    assert fingerprint(request) == protocol['expected_parent_request_sha256']
    rows = request['source_request']['evidence']
    assert sorted(r['observation_id'] for r in rows) == protocol['candidate_ids']
    authority = dict(schema_version=1,kind='real_source_preparation',
        parent=dict(root_id='project',relative_path=(OUT/'source').relative_to(ROOT).as_posix()),
        parent_receipt_sha256=parent['receipt_sha256'],source_authority_sha256=protocol['source_authority_sha256'],
        candidate_ids=protocol['candidate_ids'],grounded_fingerprints={r['observation_id']:r['admitted_sha256'] for r in rows},
        category=rows[0]['scientific_record']['category'],request_sha256=fingerprint(request))
    anchor = fingerprint(authority)
    publish_bytes(OUT/'retrieval-authority.json',canonical(authority))
    results=[]
    for strategy in protocol['strategies']:
        result = prepare_retrieval(authority,anchor,policy_for(strategy),OUT/strategy,roots=roots,deadline=deadline)
        results.append(dict(strategy=strategy,result=encode(result)))
    prepared_seconds = time.monotonic()-started
    assert prepared_seconds <= 300
    verification_start = time.monotonic()
    for result in results:
        result['replay'] = encode(verify_retrieval_preparation(OUT/result['strategy'],
            result['result']['receipt_sha256'],anchor,roots=roots,deadline=verification_start+300))
    assert not any(state['guards'].values())
    state.update(status='known_single_real_record_retrieval_verified',source_request_sha256=fingerprint(request),
                 source_parent_receipt_sha256=parent['receipt_sha256'],authority_sha256=anchor,
                 declared_real_candidates=1,results=results,preparation_seconds=prepared_seconds,
                 verification_seconds=time.monotonic()-verification_start,
                 nontrivial_real_retrieval_demonstrated=False)
    publish_bytes(OUT/'qualification.json',canonical(state))
    with (HERE/'KNOWN-REAL-QUALIFICATION.json').open('x',encoding='utf-8') as stream:
        json.dump(state,stream,indent=2)
    print(json.dumps(state))
except BaseException as error:
    state.update(status='failed',error_class=type(error).__name__,error=str(error),elapsed_seconds=time.monotonic()-started)
    publish_bytes(OUT/'failure.json',canonical(state))
    with (HERE/'KNOWN-REAL-FAILURE.json').open('x',encoding='utf-8') as stream:
        json.dump(state,stream,indent=2)
    raise
