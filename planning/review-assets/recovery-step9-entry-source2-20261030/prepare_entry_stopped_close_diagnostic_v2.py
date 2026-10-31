"""Metadata/AST-only five-check diagnostic freeze; no subject import/run."""
import ast
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def pin(path):
    path=Path(path).resolve()
    raw=path.read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def exact(p):
    assert pin(p['path'])==p
    return Path(p['path']).read_bytes()


def save(name,value):
    path=HERE/name
    with path.open('xb') as stream:
        stream.write((json.dumps(value,indent=2,sort_keys=True,ensure_ascii=True)+'\n').encode('utf-8'))
    return pin(path)


def functions(text):
    return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(text).body
            if isinstance(n,ast.FunctionDef)}


def main():
    prior_freeze_path=HERE/'ENTRY-SOURCE2-REGRESSION-FREEZE-v1.json'
    assert pin(prior_freeze_path)['sha256']=='f35a0839d8abc04ae74f223391f98775f10f0c17f010c2ebd619ab43c8acdfc5'
    old=json.loads(prior_freeze_path.read_bytes().decode('utf-8'))
    original_preparation=json.loads(exact(old['preparation']).decode('utf-8'))
    inputs=json.loads(exact(old['inputs']).decode('utf-8'))
    exact(old['source_pause'])
    assert old['source_pause']['sha256']=='2fc856163278a6521325b4865f8be77c148f72e09f35050fd6b54d60c635a54c'
    for p in old['harness'].values():exact(p)
    for p in inputs['source_map'].values():exact(p)
    original=Path(old['harness']['regressions']['path']).read_bytes().decode('utf-8')
    updated=(HERE/'entry_initial_regressions_v3.py').read_bytes().decode('utf-8')
    a=functions(original);b=functions(updated)
    assert len(a)==4 and len(b)==5 and all(b[k]==v for k,v in a.items())
    original_runner=Path(old['harness']['runner']['path']).read_bytes().decode('utf-8')
    runner=(HERE/'run_entry_source2_regressions_v2.py').read_bytes().decode('utf-8')
    ra=functions(original_runner);rb=functions(runner)
    assert ra.keys()==rb.keys()
    changed=sorted(k for k in ra if ra[k]!=rb[k])
    assert changed==['main','retain_world']
    harness=dict(support=old['harness']['support'],world=old['harness']['world'],
                 regressions=pin(HERE/'entry_initial_regressions_v3.py'),
                 runner=pin(HERE/'run_entry_source2_regressions_v2.py'))
    for p in harness.values():
        exact(p);ast.parse(Path(p['path']).read_bytes().decode('utf-8'),filename=p['path'])
    grammar=pin(HERE/'ENTRY-KERNEL2-FILEVIEW2-INDEPENDENT-STATIC-REVIEW-v1.json')
    os_peer=pin(HERE/'ENTRY-KERNEL2-STOPPED-CLOSE-CACHE-REVIEW-v1.json')
    assert grammar['sha256']=='fe4d8b6693dfc126bf086be0ef3e2144b503fff7d092ec2138a2c9edbbd70f60'
    assert os_peer['sha256']=='d3bb779aa2d83fd1ae230c23732e34cdbba185938146fda84afdb252f7cd54ff'
    methods=list(b)
    preparation=dict(schema_version=2,status='SOURCE2_HOLD_FROZEN_FIVE_CHECK_DIAGNOSTIC_BEFORE_EXECUTION',
                     source_pause=old['source_pause'],source_map=inputs['source_map'],inputs=old['inputs'],
                     harness=harness,prior_four_check_freeze=pin(prior_freeze_path),
                     prior_four_check_preparation=old['preparation'],
                     authoring_scope=original_preparation['authoring_scope'],
                     stopped_close_static_peers=[grammar,os_peer],
                     prior_static_clear_scope='40ca681e static decision is superseded by this same-F2 stopped-close HOLD; retained unchanged. No source behavior acceptance or test execution occurred.',
                     methods=methods,preserved_method_count=4,preserved_method_ASTs_equal=True,
                     runner_changed_functions=changed,
                     runner_delta='Append closed fifth method/new binding+attempt+proof names/new regression module; retain per-world stopped_close_probe evidence. Source loading/audit/deadline/error helpers and all four prior assertions unchanged.',
                     fifth_path='Actual captured FileView close uses the ordinary independently counted raw callback. That pre-entry exact synthetic callback catches ONLY the same postcommit publication MemoryError and returns None; Core records a normal wrapper return before its stopped check. Require stopped same-call scalar cache to remain UNOBSERVED while committed close BOOL1 and original error stay known.',
                     expected_source2_assertion='stopped CloseHandle normal-return path must not heal its interrupted scalar cache',
                     expected_diagnostic_outcomes={name:'FAIL' if name==methods[-1] else 'PASS' for name in methods},
                     expected_failure_is_not_source_PASS=True,
                     failure_evidence='Before the no-healing assertion, retain actual ordinal/cache-sentinel/value, bank bits/state/known value, wrapper result/return/stopped, same-error identity booleans and independent chosen-path close attempts. Existing finally preserves later cleanup/evidence errors separately.',
                     actual_helper_bytes=inputs['baseline_geometry']['early_bytes'],
                     geometry=inputs['baseline_geometry'],subject_imports=0,subject_tests=0,
                     unchanged_support_world_inputs=True,source1_replayed=False,
                     full_32_53='NOT_EXECUTED',native25='NOT_EXECUTED',
                     limitations=['Source2 remains HOLD pending the actual five-check diagnostic and a separately authorized narrow correction.',
                                  'One original cooperative60s deadline; no hard callback-free hang guarantee.',
                                  'No native/physical/real-entry/full-roster/new84/resource/scientific qualification.'])
    prep=save('ENTRY-SOURCE2-DIAGNOSTIC-PREPARATION-v2.json',preparation)
    outline=dict(status='UNBOUND_NO_EXECUTION_AUTHORITY',deadline_seconds=60,methods=methods,
                 execution_scope=None,source_pause=old['source_pause'],preparation=prep,
                 inputs=old['inputs'],source_map=inputs['source_map'],harness=harness)
    outline_pin=save('ENTRY-SOURCE2-DIAGNOSTIC-BINDING-OUTLINE-v2.json',outline)
    freeze=save('ENTRY-SOURCE2-DIAGNOSTIC-FREEZE-v2.json',
                dict(schema_version=2,status='FROZEN_BEFORE_SOURCE2_FIVE_CHECK_DIAGNOSTIC',
                     source_pause=old['source_pause'],inputs=old['inputs'],preparation=prep,
                     outline=outline_pin,harness=harness,preparer=pin(__file__),
                     author=pin(HERE/'author_entry_stopped_close_diagnostic_v2.py'),
                     preserved_four_check_freeze=pin(prior_freeze_path),subject_imports=0,subject_runs=0))
    print(json.dumps(dict(freeze=freeze,preparation=prep,outline=outline_pin,harness=harness,
                          methods=methods)))


if __name__=='__main__':
    main()
