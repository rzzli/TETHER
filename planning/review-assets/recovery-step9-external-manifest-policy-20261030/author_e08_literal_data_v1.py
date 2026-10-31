"""Independent E08 literal DATA author: no policy implementation or solver.

Expected decisions are explicitly assigned below. Automation is limited to
copying literal structures, standard canonical JSON framing/hashes and declared
field counts. There is no graph validation/traversal or subject import.
"""
import copy
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ASSETS=HERE.parent
CURRENT_REASON='CURRENT_RUN_NOT_A_STATIC_PIN'
SHA_TCB='11'*32
SHA_INPUT='22'*32
SHA_PRIOR='33'*32
SHA_CONSUMER='44'*32


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def combined(request):return canonical(dict(binding=request['binding'],envelope=request['envelope']))


def root_pin(name,size,digest):return dict(id=name,bytes=size,sha256=digest)


def pinned(name,role,size,digest,deps=()):
    return dict(id=name,role=role,state='PINNED',bytes=size,sha256=digest,reason=None,pin_dependencies=list(deps))


def current(name,role,deps=()):
    return dict(id=name,role=role,state='CURRENT',bytes=None,sha256=None,reason=CURRENT_REASON,pin_dependencies=list(deps))


def planned(name,state='PLANNED_SOURCE',reason='future source',deps=()):
    return dict(id=name,role='INPUT',state=state,bytes=None,sha256=None,reason=reason,pin_dependencies=list(deps))


def base(mode='EXECUTION',outputs=1):
    output_ids=['run.output%02d'%i for i in range(outputs)]
    binding=dict(mode=mode,current_decision_id='run.decision',current_output_ids=output_ids,
                 basis_ids=['input.a','consumer.a'],external_tcb_pins=[root_pin('root.tcb',17,SHA_TCB)],
                 prior_metadata_pins=[root_pin('prior.meta',5,SHA_PRIOR)])
    nodes=[pinned('root.tcb','EXTERNAL_TCB',17,SHA_TCB),
           pinned('prior.meta','PRIOR_APPROVED_METADATA',5,SHA_PRIOR,['root.tcb']),
           pinned('input.a','INPUT',23,SHA_INPUT,['prior.meta']),
           pinned('consumer.a','CONSUMER',31,SHA_CONSUMER,['input.a']),
           current('run.decision','CURRENT_DECISION')]
    nodes.extend(current(x,'CURRENT_OUTPUT')for x in output_ids)
    envelope=dict(schema_version=1,mode=mode,current_decision_id='run.decision',
                  current_output_ids=list(output_ids),external_anchor_ids=['root.tcb'],
                  basis_ids=['input.a','consumer.a'],nodes=nodes)
    context=None if mode=='AUTHORING' else [root_pin('input.a',23,SHA_INPUT),root_pin('consumer.a',31,SHA_CONSUMER)]
    return dict(binding=binding,envelope=envelope),context


def node(request,name):return next(n for n in request['envelope']['nodes']if n['id']==name)


def rename(request,context,old,new):
    b=request['binding'];e=request['envelope']
    for obj in (b,e):
        if obj['current_decision_id']==old:obj['current_decision_id']=new
        for key in ('current_output_ids','basis_ids'):
            obj[key]=[new if v==old else v for v in obj[key]]
    e['external_anchor_ids']=[new if v==old else v for v in e['external_anchor_ids']]
    for key in ('external_tcb_pins','prior_metadata_pins'):
        for p in b[key]:
            if p['id']==old:p['id']=new
    for n in e['nodes']:
        if n['id']==old:n['id']=new
        n['pin_dependencies']=[new if v==old else v for v in n['pin_dependencies']]
    if context is not None:
        for p in context:
            if p['id']==old:p['id']=new


def expected_report(request,status):
    b=request['binding'];e=request['envelope']
    return dict(schema_version=1,mode=e['mode'],status=status,node_count=len(e['nodes']),
                edge_count=sum(len(n['pin_dependencies'])for n in e['nodes']),
                basis_ids=list(e['basis_ids']),external_anchor_ids=list(e['external_anchor_ids']),
                prior_root_ids=[p['id']for p in b['prior_metadata_pins']],
                planned_ids=[n['id']for n in e['nodes']if n['state']=='PLANNED_SOURCE'],
                unbuilt_ids=[n['id']for n in e['nodes']if n['state']=='UNBUILT'],
                binding_sha256=hashlib.sha256(canonical(b)).hexdigest(),
                envelope_sha256=hashlib.sha256(canonical(e)).hexdigest())


def dense_edges(extra=False):
    roots=['root.r%02d'%i for i in range(33)]
    inputs=['input.n%03d'%i for i in range(127)]
    b=dict(mode='EXECUTION',current_decision_id='run.decision',current_output_ids=['run.output00'],
           basis_ids=[inputs[0]],external_tcb_pins=[root_pin(x,17,SHA_TCB)for x in roots],prior_metadata_pins=[])
    nodes=[pinned(x,'EXTERNAL_TCB',17,SHA_TCB)for x in roots]
    for i,name in enumerate(inputs):
        deps=roots[:32]+([roots[32]]if i<32 or extra and i==32 else [])
        nodes.append(pinned(name,'INPUT',1,SHA_INPUT,deps))
    nodes.extend([current('run.decision','CURRENT_DECISION'),current('run.output00','CURRENT_OUTPUT')])
    e=dict(schema_version=1,mode='EXECUTION',current_decision_id='run.decision',current_output_ids=['run.output00'],
           external_anchor_ids=roots,basis_ids=[inputs[0]],nodes=nodes)
    return dict(binding=b,envelope=e),[root_pin(inputs[0],1,SHA_INPUT)]


def exact_canonical_cap():
    # Only standard JSON byte framing is searched here, never graph acceptance.
    roots=[('R%02d.'%i).ljust(128,'x')for i in range(16)]
    inputs=['input.p%02d'%i for i in range(80)]
    b=dict(mode='AUTHORING',current_decision_id='run.decision',current_output_ids=['run.output00'],
           basis_ids=[inputs[0]],external_tcb_pins=[root_pin(x,17,SHA_TCB)for x in roots],prior_metadata_pins=[])
    nodes=[pinned(x,'EXTERNAL_TCB',17,SHA_TCB)for x in roots]
    nodes.extend(planned(x,reason='p')for x in inputs)
    nodes.extend([current('run.decision','CURRENT_DECISION'),current('run.output00','CURRENT_OUTPUT')])
    e=dict(schema_version=1,mode='AUTHORING',current_decision_id='run.decision',current_output_ids=['run.output00'],
           external_anchor_ids=roots,basis_ids=[inputs[0]],nodes=nodes)
    request=dict(binding=b,envelope=e)
    for item in nodes[16:96]:
        for target in roots:
            item['pin_dependencies'].append(target)
            if len(combined(request))>131072:
                item['pin_dependencies'].pop()
                gap=131072-len(combined(request))
                assert 0<=gap<=255
                nodes[16]['reason']+='x'*gap
                assert len(combined(request))==131072
                return request,None
    raise AssertionError('bounded literal framing recipe did not reach cap')


def main():
    contract=pin(HERE/'E08-EXTERNAL-MANIFEST-POLICY-CONTRACT-DRAFT-v2.json')
    assert contract['sha256']=='28579307416260293c8ffbdee71e076ec078101470a846ccb9a75e59b8e4254c'
    clarification=pin(HERE/'E08-EXTERNAL-MANIFEST-POLICY-CLARIFICATIONS-DRAFT-v1.json')
    assert clarification['sha256']=='8ac0c4ce0e62a88a09949f57a4361111a66bb6c0f7a93d7982f78e48a0edf098'
    vectors=[]
    def add(name,request,context,code=None,status=None,note=None):
        assert (code is None)!=(status is None)
        outcome=dict(kind='REFUSAL',code=code)if code else dict(kind='REPORT',report=expected_report(request,status))
        try:framing=dict(canonical_combined_utf8_bytes=len(combined(request)))
        except UnicodeEncodeError:framing=dict(canonical_combined_utf8_bytes=None,reason='INVALID_UNICODE_LITERAL; encoding is never a successful outcome')
        vectors.append(dict(id=name,request=request,entry_basis_pins=context,expected=outcome,
                            expected_boundary='CORE_POLICY_AFTER_ORIGINAL_START',framing=framing,note=note))
    def fresh():return base()
    q,c=fresh();add('allowed_external_and_prior_roots',q,c,status='EXECUTION_BASIS_VALIDATED')
    q,c=fresh();node(q,'run.decision')['pin_dependencies']=['consumer.a'];node(q,'run.output00')['pin_dependencies']=['run.decision']
    add('allowed_downstream_current_provenance',q,c,status='EXECUTION_BASIS_VALIDATED')
    q,c=base('AUTHORING');q['envelope']['nodes']+= [planned('input.future',deps=['input.unbuilt']),planned('input.unbuilt','UNBUILT','not built')]
    node(q,'consumer.a')['pin_dependencies']=['input.future']
    unresolved=copy.deepcopy(q)
    add('authoring_planned_unbuilt_descendants',q,c,status='AUTHORING_ONLY')
    q=copy.deepcopy(unresolved);q['binding']['mode']=q['envelope']['mode']='EXECUTION'
    add('execution_unbuilt_static_descendants',q,fresh()[1],code='POLICY_UNBUILT')
    q,c=fresh();q['envelope']['nodes'].append(planned('input.ignored','UNBUILT','not selected'))
    add('execution_unbuilt_nonbasis_still_refuses',q,c,code='POLICY_UNBUILT')
    for name,target in (('forbidden_decision_direct','run.decision'),('forbidden_output_direct','run.output00')):
        q,c=fresh();node(q,'input.a')['pin_dependencies']=[target]
        add(name,q,c,code='POLICY_FORBIDDEN_ANCESTRY')
    q,c=fresh();q['envelope']['nodes'].append(pinned('input.middle','INPUT',1,SHA_INPUT,['run.output00']))
    node(q,'input.a')['pin_dependencies']=['input.middle']
    add('forbidden_output_transitive_via_pinned_input',q,c,code='POLICY_FORBIDDEN_ANCESTRY')
    q,c=fresh();q['envelope']['nodes'].append(pinned('consumer.ignored','CONSUMER',1,SHA_INPUT,['run.decision']))
    add('forbidden_ancestry_outside_basis',q,c,code='POLICY_FORBIDDEN_ANCESTRY')
    q,c=fresh();node(q,'input.a')['pin_dependencies']=['input.a'];add('cycle_self',q,c,code='POLICY_CYCLE')
    q,c=fresh();node(q,'input.a')['pin_dependencies']=['consumer.a'];add('cycle_mutual',q,c,code='POLICY_CYCLE')
    q,c=fresh();node(q,'input.a')['pin_dependencies']=['input.middle']
    q['envelope']['nodes'].append(pinned('input.middle','INPUT',1,SHA_INPUT,['consumer.a']))
    add('cycle_transitive_three_nodes',q,c,code='POLICY_CYCLE')
    q,c=fresh();node(q,'root.tcb')['pin_dependencies']=['prior.meta'];node(q,'prior.meta')['pin_dependencies']=[]
    add('external_tcb_dependency_role_refuses',q,c,code='POLICY_DEPENDENCY_ROLE')
    q,c=fresh();node(q,'prior.meta')['pin_dependencies']=['input.a'];node(q,'input.a')['pin_dependencies']=[]
    add('prior_metadata_dependency_role_refuses',q,c,code='POLICY_DEPENDENCY_ROLE')
    q,c=fresh();node(q,'input.a')['pin_dependencies']=['missing.node'];add('unknown_dependency',q,c,code='POLICY_UNKNOWN_NODE')
    q,c=fresh();q['envelope']['nodes'].append(copy.deepcopy(node(q,'input.a')));add('identical_duplicate_node',q,c,code='POLICY_DUPLICATE_ID')
    q,c=fresh();n=copy.deepcopy(node(q,'input.a'));n['sha256']='55'*32;q['envelope']['nodes'].append(n)
    add('conflicting_duplicate_node',q,c,code='POLICY_PIN_CONFLICT')
    q,c=fresh();node(q,'input.a')['pin_dependencies']=['prior.meta','prior.meta'];add('duplicate_dependency',q,c,code='POLICY_DUPLICATE_ID')
    q,c=fresh();q['envelope']['mode']='AUTHORING';add('binding_mode_mismatch',q,c,code='POLICY_BINDING_MISMATCH')
    q,c=fresh();q['envelope']['basis_ids'].reverse();add('binding_basis_order_mismatch',q,c,code='POLICY_BINDING_MISMATCH')
    q,c=fresh();node(q,'root.tcb')['sha256']='66'*32;add('binding_external_pin_mismatch',q,c,code='POLICY_BINDING_MISMATCH')
    q,c=fresh();n=node(q,'run.decision');n.update(role='EXTERNAL_TCB',state='PINNED',bytes=1,sha256='77'*32,reason=None)
    add('current_identity_relabelled_as_tcb',q,c,code='POLICY_BINDING_MISMATCH')
    q,c=fresh();q['envelope']['approved']=True;add('serialized_approved_flag_is_extra_key',q,c,code='POLICY_SCHEMA')
    q,c=fresh();node(q,'input.a')['role']='READY_INPUT';add('unknown_role',q,c,code='POLICY_DOMAIN')
    q,c=fresh();node(q,'run.decision').update(state='PINNED',bytes=1,sha256='77'*32,reason=None)
    add('current_role_cannot_use_pinned_state',q,c,code='POLICY_DOMAIN')
    q,c=fresh();node(q,'input.a')['bytes']=False;add('boolean_bytes_not_integer_zero',q,c,code='POLICY_DOMAIN')
    q,c=base('AUTHORING');node(q,'input.a')['bytes']=(1<<63)-1;add('signed64_byte_maximum_valid_metadata',q,c,status='AUTHORING_ONLY')
    q,c=fresh();node(q,'input.a')['bytes']=1<<63;add('signed64_byte_one_over_domain',q,c,code='POLICY_DOMAIN')
    q,c=fresh();node(q,'input.a')['sha256']=None;add('pinned_hash_null_is_not_unbuilt',q,c,code='POLICY_DOMAIN')
    q,c=fresh();rename(q,c,'input.a','A'+'x'*127);add('id_128_ascii_bytes_valid',q,c,status='EXECUTION_BASIS_VALIDATED')
    q,c=fresh();rename(q,c,'input.a','9'+'x'*128);add('id_129_length_precedes_pattern',q,c,code='POLICY_LIMIT')
    q,c=fresh();rename(q,c,'input.a','input.λ');add('id_nonascii_valid_length_domain',q,c,code='POLICY_DOMAIN')
    q,c=base('AUTHORING');q['envelope']['nodes'].append(planned('input.future',reason='é'*256))
    add('reason_256_unicode_codepoints_valid',q,c,status='AUTHORING_ONLY')
    q,c=base('AUTHORING');q['envelope']['nodes'].append(planned('input.future',reason='r'*256+'\ud800'))
    add('reason_257_length_precedes_unicode',q,c,code='POLICY_LIMIT')
    q,c=base('AUTHORING');q['envelope']['nodes'].append(planned('input.future',reason='\ud800'))
    add('reason_lone_surrogate_domain',q,c,code='POLICY_DOMAIN')
    q,c=base(outputs=14);add('current_outputs_14_valid',q,c,status='EXECUTION_BASIS_VALIDATED')
    q,c=base(outputs=15);add('current_outputs_15_limit',q,c,code='POLICY_LIMIT')
    q,c=fresh();q['envelope']['nodes'].extend(pinned('input.extra%03d'%i,'INPUT',1,SHA_INPUT)for i in range(250))
    add('nodes_256_valid',q,c,status='EXECUTION_BASIS_VALIDATED')
    q,c=fresh();q['envelope']['nodes'].extend(pinned('input.extra%03d'%i,'INPUT',1,SHA_INPUT)for i in range(251))
    add('nodes_257_limit',q,c,code='POLICY_LIMIT')
    q,c=dense_edges();assert sum(len(n['pin_dependencies'])for n in q['envelope']['nodes'])==4096
    assert len(combined(q))<=131072;add('declared_edges_4096_valid',q,c,status='EXECUTION_BASIS_VALIDATED')
    q,c=dense_edges(True);assert sum(len(n['pin_dependencies'])for n in q['envelope']['nodes'])==4097
    add('declared_edges_4097_limit',q,c,code='POLICY_LIMIT')
    q,c=exact_canonical_cap();add('canonical_combined_131072_valid',q,c,status='AUTHORING_ONLY')
    q=copy.deepcopy(q);node(q,'input.p00')['reason']+='x';assert len(combined(q))==131073
    add('canonical_combined_131073_limit',q,None,code='POLICY_LIMIT')
    q,c=fresh();c.pop();add('entry_plan_basis_count_mismatch',q,c,code='POLICY_BASIS_MISMATCH')
    q,c=fresh();c[0]['sha256']='88'*32;add('entry_plan_basis_pin_mismatch',q,c,code='POLICY_BASIS_MISMATCH')
    q,c=fresh();q['binding']['external_tcb_pins'].append(copy.deepcopy(q['binding']['external_tcb_pins'][0]))
    add('identical_duplicate_external_pin',q,c,code='POLICY_DUPLICATE_ID')
    q,c=fresh();n=copy.deepcopy(q['binding']['external_tcb_pins'][0]);n['sha256']='99'*32;q['binding']['external_tcb_pins'].append(n)
    add('conflicting_duplicate_external_pin',q,c,code='POLICY_PIN_CONFLICT')
    q,c=fresh();q['binding']['prior_metadata_pins'].append(copy.deepcopy(q['binding']['external_tcb_pins'][0]))
    add('cross_role_pin_overlap_identical_content',q,c,code='POLICY_PIN_CONFLICT')
    q,c=fresh();q['binding']['basis_ids']=['input.a','input.a'];q['envelope']['basis_ids']=['input.a','input.a']
    add('duplicate_ordinary_basis_id',q,c,code='POLICY_DUPLICATE_ID')
    q,c=fresh();q['binding']['basis_ids'][0]='run.decision';q['envelope']['basis_ids'][0]='run.decision'
    add('binding_basis_current_role_overlap',q,c,code='POLICY_PIN_CONFLICT')
    q,c=fresh();q['binding']['mode']=q['envelope']['mode']='RUN';add('unknown_mode_domain',q,c,code='POLICY_DOMAIN')
    q,c=base(outputs=2);node(q,'run.output00')['pin_dependencies']=['run.output01'];node(q,'run.output01')['pin_dependencies']=['run.output00']
    add('current_output_mutual_cycle_outside_basis',q,c,code='POLICY_CYCLE')
    assert len(vectors)==52 and len({v['id']for v in vectors})==52
    for ordinal,v in enumerate(vectors,1):v['ordinal']=ordinal
    result=dict(schema_version=1,status='READABLE_INDEPENDENT_LITERAL_DRAFT_NOT_FROZEN_NO_SUBJECT',
                effective_contract=[contract,clarification],
                authoring_scope=pin(ASSETS/'recovery-step9-entry-contract-tests-20261030'/'E08-POLICY-CONTRACT-AUTHORING-SCOPE-v1.json'),
                vector_count=len(vectors),vectors=vectors,
                expectation_method='Acceptance/refusal categories explicitly assigned by the independent author. No graph solver/traversal/reference policy implementation is used. Standard JSON framing/hashes and declared field counts only are automated.',
                entry_basis_context='Harness-only independently frozen FileSpec pin expectations; excluded from request/canonical bytes/hashes. A future actual test must not derive both comparison sides from a report.',
                bytes_and_ids='Invented declared ID-only metadata and digest labels, not authenticated files, target paths or actual payload fingerprints.',
                no_authority='Every expected report has exactly12 data fields. Neither accepted status constructs an Origin/nonce/Core/ref/continuation/lease/child/image or live file admission.',
                future_genuine_controls=['Executing-kernel binding brand/foreign namespace, immutable capture, same-Core gate and first-open barrier.',
                    'Original clock/prepared-versus-issued report interruption and cold non-healing getters.',
                    'Fresh legal CloseHandle after a later unrelated owner failure remains permitted under existing rules.'],
                activity=dict(policy_implementation=False,subject_imports=0,subject_runs=0,original_targets_followed=False,native25=False),
                qualification=False)
    out=HERE/'E08-INDEPENDENT-LITERAL-CORPUS-DRAFT-v1.json'
    raw=(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=True)+'\n').encode('utf-8')
    with out.open('xb')as f:f.write(raw)
    print(json.dumps(dict(corpus=pin(out),vectors=len(vectors),reports=sum(v['expected']['kind']=='REPORT'for v in vectors),refusals=sum(v['expected']['kind']=='REFUSAL'for v in vectors))))


if __name__=='__main__':main()
