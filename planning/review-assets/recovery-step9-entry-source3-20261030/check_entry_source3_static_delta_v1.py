"""Exact static guard/namespace/preparation review; no subject imports."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/'recovery-step9-entry-source2-20261030'


def pin(path):
    path=Path(path).resolve();raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def norm(text):
    for name in ('preflight_entry_kernel','preflight_owner_ops','preflight_file_view'):
        text=text.replace(name+'_v2',name+'_v3')
    return text


def dump(node):return ast.dump(node,include_attributes=False)


def main():
    files=('preflight_entry_kernel','preflight_owner_ops','preflight_file_view')
    verified={}
    for name in files:
        before=(OLD/(name+'_v2.py')).read_bytes().decode('utf-8')
        path=HERE/(name+'_v3.py');after=path.read_bytes().decode('utf-8')
        a=ast.parse(norm(before));b=ast.parse(after)
        removed=[]
        if name=='preflight_entry_kernel':
            state=next(n for n in b.body if isinstance(n,ast.ClassDef) and n.name=='KernelState')
            for method,variable in (('_cache_committed_fact','call'),('_reconcile_native','c')):
                fn=next(n for n in state.body if isinstance(n,ast.FunctionDef) and n.name==method)
                position=1 if isinstance(fn.body[0],ast.Expr) and isinstance(fn.body[0].value,ast.Constant) and type(fn.body[0].value.value)is str else 0
                expected=ast.parse('if '+variable+'.stopped:\n    error=self.primary\n    if error is not None:raise error\n    raise KernelRefusal(\'RAW_RETURN_UNKNOWN\')\n').body[0]
                assert dump(fn.body[position])==dump(expected)
                del fn.body[position]
                removed.append('KernelState.'+method)
            assert removed==['KernelState._cache_committed_fact','KernelState._reconcile_native']
        assert dump(a)==dump(b)
        verified[name]=dict(pin=pin(path),exact_behavior_delta=removed,
                            all_other_AST_equal_after_namespace=True)
    freeze_path=HERE/'ENTRY-SOURCE3-REGRESSION-FREEZE-v1.json'
    freeze=json.loads(freeze_path.read_bytes().decode('utf-8'))
    assert pin(freeze_path)['sha256']=='fb8987fffc4074e9884b7e168a95c6e28c72be8f874d56ffce39c0306ae0d5f2'
    for p in [freeze['inputs'],freeze['preparation'],freeze['outline'],freeze['source_pause'],*freeze['harness'].values()]:
        assert pin(p['path'])==p
    data=json.loads(Path(freeze['inputs']['path']).read_bytes().decode('utf-8'))
    for p in data['source_map'].values():assert pin(p['path'])==p
    before=ast.parse((OLD/'entry_initial_regressions_v3.py').read_bytes().decode('utf-8'))
    after=ast.parse((HERE/'entry_initial_regressions_v4.py').read_bytes().decode('utf-8'))
    a={n.name:dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert len(a)==5 and a==b
    result=dict(schema_version=1,status='CLEAR_STATIC_SOURCE3_TWO_GUARD_AND_UNCHANGED_FIVE_CHECK_PREPARATION_ONLY',
                material_blockers=[],checker=pin(__file__),source_pause=freeze['source_pause'],
                sources=verified,regression_freeze=pin(freeze_path),actual_helper_bytes=99000,
                geometry=data['baseline_geometry'],five_assertion_ASTs_unchanged=True,
                source2_actual_hold=pin(OLD/'ENTRY-SOURCE2-DIAGNOSTIC-INDEPENDENT-ACTUAL-REVIEW-v2.json'),
                correction='Both healthy-cache and reconcile entries reject only the current stopped call before any repair, rethrowing the retained primary object or typed RAW_RETURN_UNKNOWN fallback. A fresh nonstopped CloseHandle under an earlier owner error retains its cleanup path. No other behavior changed.',
                source_imports=0,subject_runs=0,
                limitations=['Static clearance only; five-test Source3 result pending Root binding/execution.',
                             'Full32/53/native25 and all real-entry/native/physical/full-roster/new84/resource/science qualifications remain pending.'])
    out=HERE/'ENTRY-SOURCE3-FIVE-REGRESSION-INDEPENDENT-STATIC-REVIEW-v1.json'
    with out.open('xb') as f:f.write((json.dumps(result,indent=2,sort_keys=True)+'\n').encode('utf-8'))
    print(json.dumps(dict(review=pin(out))))


if __name__=='__main__':
    main()
