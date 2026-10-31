"""Data-only literal framing QC, not an E08 policy validator/reference solver."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BINDING_KEYS={'mode','current_decision_id','current_output_ids','basis_ids','external_tcb_pins','prior_metadata_pins'}
PIN_KEYS={'id','bytes','sha256'}
REPORT_KEYS={'schema_version','mode','status','node_count','edge_count','basis_ids','external_anchor_ids',
             'prior_root_ids','planned_ids','unbuilt_ids','binding_sha256','envelope_sha256'}


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')


def main():
    path=HERE/'E08-INDEPENDENT-LITERAL-CORPUS-DRAFT-v1.json'
    data=json.loads(path.read_bytes().decode('utf-8'));vectors=data['vectors']
    assert len(vectors)==data['vector_count']==52 and len({r['id']for r in vectors})==52
    reports=refusals=0
    for ordinal,v in enumerate(vectors,1):
        assert v['ordinal']==ordinal and set(v['request'])=={'binding','envelope'}
        b=v['request']['binding'];e=v['request']['envelope']
        assert set(b)==BINDING_KEYS and v['expected_boundary']=='CORE_POLICY_AFTER_ORIGINAL_START'
        # Genuine constructor-shell reachability only: deliberately no enum,
        # scalar-domain, role, graph, ancestry, uniqueness or policy decision.
        for key in ('current_output_ids','basis_ids','external_tcb_pins','prior_metadata_pins'):
            assert type(b[key])is list and len(b[key])<=256
        for key in ('mode','current_decision_id'):
            assert b[key] is None or type(b[key])in(str,int,float,bool)
        for key in ('current_output_ids','basis_ids'):
            assert all(value is None or type(value)in(str,int,float,bool)for value in b[key])
        for key in ('external_tcb_pins','prior_metadata_pins'):
            for p in b[key]:
                assert type(p)is dict and set(p)==PIN_KEYS
                assert all(value is None or type(value)in(str,int,float,bool)for value in p.values())
        try:
            size=len(canonical(dict(binding=b,envelope=e)))
            assert v['framing']['canonical_combined_utf8_bytes']==size
        except UnicodeEncodeError:
            assert v['framing']['canonical_combined_utf8_bytes'] is None
        expected=v['expected']
        if expected['kind']=='REPORT':
            reports+=1;r=expected['report']
            assert set(r)==REPORT_KEYS and r['schema_version']==1
            assert r['mode']==e['mode'] and r['status']in('AUTHORING_ONLY','EXECUTION_BASIS_VALIDATED')
            assert r['node_count']==len(e['nodes']) and r['edge_count']==sum(len(n['pin_dependencies'])for n in e['nodes'])
            assert r['binding_sha256']==hashlib.sha256(canonical(b)).hexdigest()
            assert r['envelope_sha256']==hashlib.sha256(canonical(e)).hexdigest()
            assert r['basis_ids']==e['basis_ids'] and r['external_anchor_ids']==e['external_anchor_ids']
            assert r['prior_root_ids']==[p['id']for p in b['prior_metadata_pins']]
            assert r['planned_ids']==[n['id']for n in e['nodes']if n['state']=='PLANNED_SOURCE']
            assert r['unbuilt_ids']==[n['id']for n in e['nodes']if n['state']=='UNBUILT']
        else:
            refusals+=1;assert expected['kind']=='REFUSAL' and type(expected['code'])is str
    by={v['id']:v for v in vectors}
    assert reports==10 and refusals==42
    assert by['canonical_combined_131072_valid']['framing']['canonical_combined_utf8_bytes']==131072
    assert by['canonical_combined_131073_limit']['framing']['canonical_combined_utf8_bytes']==131073
    assert len(by['nodes_256_valid']['request']['envelope']['nodes'])==256
    assert len(by['nodes_257_limit']['request']['envelope']['nodes'])==257
    for name,count in (('declared_edges_4096_valid',4096),('declared_edges_4097_limit',4097)):
        assert sum(len(n['pin_dependencies'])for n in by[name]['request']['envelope']['nodes'])==count
    result=dict(schema_version=1,status='PASS_LITERAL_SHAPE_AND_FRAMING_ONLY_NO_POLICY_EVALUATION',
                corpus=pin(path),checker=pin(__file__),author_helper=pin(HERE/'author_e08_literal_data_v1.py'),
                vector_count=52,explicit_report_goldens=10,explicit_refusal_goldens=42,
                groups_passed=6,groups=['52 identities/ordinals/request wrapper shapes',
                    'genuine constructor-shell reachability without semantic forgery',
                    'canonical combined framing/Unicode capture distinctions',
                    'exact12-field report hashes/counts/list framing',
                    'literal node/edge/byte boundary quantities',
                    'all expected classification fields remain literal, no validator/graph solver'],
                graph_cycles_or_ancestry_evaluated=False,policy_implementation_authored=False,
                subject_imports=0,subject_runs=0,original_targets_followed=False,qualification=False)
    out=HERE/'E08-INDEPENDENT-LITERAL-FRAMING-PROOF-DRAFT-v1.json'
    with out.open('xb')as f:f.write((json.dumps(result,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    print(json.dumps(dict(proof=pin(out),corpus=pin(path),reports=reports,refusals=refusals)))


if __name__=='__main__':main()
