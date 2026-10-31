"""Independent bounded Source2 AST/pin review; never imports reviewed code."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
OLD=HERE.parent/'recovery-step9-entry-source-20261029'


def pin(path):
    path=Path(path).resolve()
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def normalized(path):
    text=Path(path).read_bytes().decode('utf-8')
    for name in ('preflight_entry_kernel','preflight_owner_ops','preflight_file_view'):
        text=text.replace(name+'_v1',name+'_v2')
    return text


def methods(tree,prefix=''):
    result={}
    for n in tree.body:
        if isinstance(n,ast.ClassDef):
            result.update(methods(n,prefix+n.name+'.'))
        elif isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
            result[prefix+n.name]=ast.dump(n,include_attributes=False)
    return result


def other_tree(tree,ignore_slots=False):
    # Compare every non-function declaration/import/constant too. The only
    # permitted structural addition is the four separate delivery slots.
    def strip(body,class_name=''):
        result=[]
        for n in body:
            if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):
                continue
            if isinstance(n,ast.ClassDef):
                n.body=strip(n.body,n.name)
            if ignore_slots and class_name=='CallState' and isinstance(n,ast.Assign):
                if any(isinstance(t,ast.Name) and t.id=='__slots__' for t in n.targets):
                    n.value.elts=[x for x in n.value.elts if not (isinstance(x,ast.Constant) and
                                  x.value in ('_python_scalar','_python_count','_python_error_value','_python_error_definition'))]
            result.append(n)
        return result
    tree.body=strip(tree.body)
    return ast.dump(tree,include_attributes=False)


def main():
    pause_path=HERE/'ENTRY-SOURCE-PAUSE-v2.json'
    pause=json.loads(pause_path.read_bytes().decode('utf-8'))
    assert pin(pause_path)['sha256']=='2fc856163278a6521325b4865f8be77c148f72e09f35050fd6b54d60c635a54c'
    delta_path=HERE/'ENTRY-SOURCE-CORRECTION-DELTA-v2.json'
    delta=json.loads(delta_path.read_bytes().decode('utf-8'))
    results={}
    for role,rows in delta['function_deltas'].items():
        before=ROOT/rows['before']['path'];after=ROOT/rows['after']['path']
        for path,wanted in ((before,rows['before']),(after,rows['after'])):
            p=pin(path)
            assert p['bytes']==wanted['bytes'] and p['sha256']==wanted['sha256']
        old_text=normalized(before);new_text=normalized(after)
        a=methods(ast.parse(old_text));b=methods(ast.parse(new_text))
        changed=sorted(k for k in a.keys()&b.keys() if a[k]!=b[k])
        added=sorted(b.keys()-a.keys());removed=sorted(a.keys()-b.keys())
        unchanged=sum(a[k]==b[k] for k in a.keys()&b.keys())
        assert changed==rows['changed'] and added==rows['added'] and removed==rows['removed']
        assert unchanged==rows['unchanged_function_AST_count']
        assert other_tree(ast.parse(old_text),True)==other_tree(ast.parse(new_text),True)
        results[role]=dict(changed=changed,added=added,removed=removed,unchanged=unchanged,
                           other_AST_equal_after_exact_namespace_and_delivery_slots=True,
                           source=pin(after))
    old_methods=methods(ast.parse((OLD/'entry_initial_regressions_v1.py').read_bytes().decode('utf-8')))
    new_methods=methods(ast.parse((HERE/'entry_initial_regressions_v2.py').read_bytes().decode('utf-8')))
    assert all(new_methods[k]==v for k,v in old_methods.items()) and len(old_methods)==3 and len(new_methods)==4
    freeze_path=HERE/'ENTRY-SOURCE2-REGRESSION-FREEZE-v1.json'
    freeze=json.loads(freeze_path.read_bytes().decode('utf-8'))
    for name in ('preparation','inputs','outline','preparer','adaptation_author'):
        p=freeze[name];assert pin(p['path'])==p
    for p in freeze['harness'].values():assert pin(p['path'])==p
    inputs=json.loads(Path(freeze['inputs']['path']).read_bytes().decode('utf-8'))
    assert inputs['baseline_geometry']['early_bytes']==99000
    assert inputs['baseline_geometry']['captured_bytes']==99068
    peer_path=HERE/'ENTRY-SOURCE2-REGRESSION-HARNESS-INDEPENDENT-STATIC-REVIEW-v1.json'
    source1_proof=OLD/'ENTRY-SOURCE1-SMOKE-PROOF-v1.json'
    assert pin(source1_proof)['sha256']=='6ec80005b91a664c6016b2beed48a74f41239827a08d8b112c45f2b9ab5865a3'
    verdict=dict(schema_version=1,
                 status='CLEAR_STATIC_SOURCE2_THREE_FIX_BATCH_AND_FOUR_REGRESSION_PREPARATION_ONLY',
                 material_blockers=[],source_pause=pin(pause_path),author_delta=pin(delta_path),
                 checker=pin(__file__),source_deltas=results,
                 regression_freeze=pin(freeze_path),harness_static_peer=pin(peer_path),
                 original_three_method_ASTs_unchanged=True,
                 first_source1_actual_setup_failure=pin(source1_proof),
                 reviewed_corrections=[
                     dict(id='F3',result='Constructor validates the actual invoke_reserved method; no alias or alternate backend.'),
                     dict(id='F1',result='The same immutable SinkFacade delegates close_journal to the unchanged backend close callback; existing owner callback ACK/clock ordering remains.'),
                     dict(id='F2',result='Original Python delivery is retained separately before native publication. All four axes publish to the canonical bank before optional authority caches. committed_fact is read-only and returns UNOBSERVED unless COMMITTED; handle/count/fold/cold reports/raw snapshot facts/Ops close/wire use committed bank authority. The exception path no longer reconciles caches; report/getter paths do not heal or retry interrupted work.'),
                     dict(id='F2_CONVERSE',result='The supplemental authored check throws after actual COMMITTED publication and before cache acknowledgment, requiring known HANDLE1000 in bank/cold/raw projections, unchanged UNOBSERVED cache, same original error and one cleanup close.')],
                 native_NULL='Raw committed HANDLE bits0 stays integer0 in the copied eight-axis observation. ROLE1 handle interpretation may emit NULL only for observed committed handle-kind zero. Uncommitted raw bits never grant NULL/handle/count authority.',
                 geometry=inputs['baseline_geometry'],
                 chronology='Only F3 was dynamically reproduced on Source1. F1/F2 were NOT_REACHED. Three original checks predate Source2; supplemental converse predates execution but was authored during Source2 drafting.',
                 subject_imports=0,subject_tests=0,
                 remaining=['Root separate execution binding required; this record claims static preparation only.',
                            'Four-regression results, full32/53 source suite and narrower native25 data/ownership controls remain pending.',
                            'Native/physical/real-first-entry/full-roster/new84/resource/scientific qualification remains false.'])
    out=HERE/'ENTRY-SOURCE2-INDEPENDENT-STATIC-REVIEW-v1.json'
    raw=(json.dumps(verdict,indent=2,sort_keys=True,ensure_ascii=True)+'\n').encode('utf-8')
    with out.open('xb') as f:f.write(raw)
    md=HERE/'ENTRY-SOURCE2-INDEPENDENT-STATIC-REVIEW-v1.md'
    text=('Source2 is clear for Root to bind the four regression checks. This is a static decision, not behavioral acceptance.\n\n'
          'The exact source delta closes the constructor method mismatch, sink close-journal interface, and committed-bank/cache-authority ordering. Independent AST comparisons match the bounded author delta; only the four separate Python delivery slots and coherent module spellings change outside functions. The first three test bodies remain exact, with one supplemental postcommit-cache-failure check.\n\n'
          'Actual helper prefix: 99,000 bytes; captured inputs: 99,068 bytes. N5/B3/M3, Q7/R87/C117/E234. Kernel120,885 bytes is separately pinned pre-entry TCB. Source1 dynamically reached only its constructor failure; the downstream defects were not reproduced there. No reviewed source was imported or executed for this review.\n\n'
          'The full source suite, native/physical entry, full real roster, new84 runtime, resources and scientific/human gates remain pending.\n')
    with md.open('xb') as f:f.write(text.encode('utf-8'))
    print(json.dumps(dict(verdict=pin(out),markdown=pin(md),results=results)))


if __name__=='__main__':
    main()
