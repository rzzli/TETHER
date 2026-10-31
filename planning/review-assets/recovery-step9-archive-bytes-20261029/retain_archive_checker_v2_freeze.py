"""Retain metadata/AST evidence only; never invoke the archive checker."""
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'CAPTURED-ARCHIVE-CHECKER-FREEZE-v2.json'

def pin(name):
    path = HERE / name
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def dump(node):
    return ast.dump(node, include_attributes=False)

def main():
    assert not OUT.exists(), 'Preserve the first retention'
    old = (HERE / 'captured_archive_v1.py').read_text(encoding='utf-8')
    new = (HERE / 'captured_archive_v2.py').read_text(encoding='utf-8')
    replacements = [
        ('"""Captured native-v7 archive graph only; no paths, files, SDK or native calls.',
         '"""Captured native-v7 archive v2: callback and one-line marker corrections.'),
        ("_need(raw.endswith(b'\\n') and not raw.endswith(b'\\r\\n') and not raw.startswith(b'\\xef\\xbb\\xbf'),'JSON_LF_or_BOM:'+node)",
         "_need(raw.find(b'\\n')==len(raw)-1 and b'\\r' not in raw and not raw.startswith(b'\\xef\\xbb\\xbf'),'JSON_LF_or_BOM:'+node)"),
        ("    if not callable(check):raise TypeError('required_deadline_callback')\n    check()",
         "    if not callable(check):raise TypeError('required_deadline_callback')\n    caller_check=check;callback_failure=[None]\n    def check():\n        try:caller_check()\n        except BaseException as error:\n            callback_failure[0]=error\n            raise\n    check()"),
        ("    except _Bad as error:bad=True;a.issues.append(str(error))",
         "    except _Bad as error:\n        if callback_failure[0] is not None:raise callback_failure[0]\n        bad=True;a.issues.append(str(error))"),
    ]
    transformed = old
    for before, after in replacements:
        assert transformed.count(before) == 1
        transformed = transformed.replace(before, after, 1)
    assert transformed == new
    old_nodes = ast.parse(old).body
    new_nodes = ast.parse(new).body
    assert len(old_nodes) == len(new_nodes)
    unchanged = []
    changed = []
    for index, (left, right) in enumerate(zip(old_nodes, new_nodes)):
        label = getattr(left, 'name', f'top_level_{index}')
        if dump(left) == dump(right):
            unchanged.append(label)
        else:
            changed.append(label)
    assert changed == ['top_level_0', '_Analysis', 'check_archive']
    old_class = next(n for n in old_nodes if isinstance(n, ast.ClassDef) and n.name == '_Analysis')
    new_class = next(n for n in new_nodes if isinstance(n, ast.ClassDef) and n.name == '_Analysis')
    class_equal = []
    for left, right in zip(old_class.body, new_class.body):
        if getattr(left, 'name', None) == 'json':
            continue
        assert dump(left) == dump(right)
        class_equal.append(getattr(left, 'name', '<class statement>'))
    proof = json.loads((HERE / 'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v2.json').read_text(encoding='utf-8'))
    assert proof['status'] == 'passed' and proof['methods'] == 10
    assert proof['inputs_unchanged'] is True
    assert not proof['failures'] and not proof['errors']
    assert len(proof['frozen_case_results']) == 32
    assert proof['inputs']['captured_archive_v2.py'] == pin('captured_archive_v2.py')
    assert proof['checker'] == pin('check_captured_archive_v2.py')
    names = [
        'ARCHIVE-CHECKER-SOURCE-ROOT-DECISION-v1.json',
        'CAPTURED-NATIVE-ARCHIVE-PREPARATION-ACCEPTANCE-v3.json',
        'CAPTURED-NATIVE-ARCHIVE-CONTRACT-v3.json',
        'CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json',
        'CAPTURED-NATIVE-ARCHIVE-FIXTURE-FREEZE-v3.json',
        'captured_archive_v1.py', 'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v1.json',
        'CAPTURED-NATIVE-ARCHIVE-SELF-REVIEW-BEFORE-v2.json',
        'captured_archive_v2.py', 'check_captured_archive_v2.py',
        'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v2.json',
        'CAPTURED-ARCHIVE-EFFECTIVE-V3-v2.md', Path(__file__).name,
    ]
    record = dict(
        schema_version=1, status='frozen_source_pure_candidate_for_independent_review',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        inputs={name:pin(name) for name in names},
        exact_byte_transform_matches=True, replacement_count=len(replacements),
        changed_top_level_ASTs=changed, unchanged_top_level_ASTs=unchanged,
        unchanged_analysis_class_members=class_equal,
        methods=10, frozen_synthetic_projections=32,
        correction_scope=['required callback exceptions propagate with original identity',
                          'one actual terminal LF and no other actual LF/CR in JSON documents'],
        historical_note='v1 first passed; two defects were discovered and witnessed afterward; v1 was preserved',
        checker_or_tests_rerun_for_this_record=False,
        actual_old_archive_capture_or_replay=False,
        SDK_OS_native_model_operations=0, CPU_GGUF_oldpack_reads=0,
        profile_qualified=False, originals_authenticated=False,
        actual_directory_complete=False, source_qualified=False,
        independent_peer_acceptance=False,
    )
    with OUT.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(record, handle, sort_keys=True, indent=2)
        handle.write('\n')
    print(json.dumps(dict(record=pin(OUT.name), methods=10, frozen_synthetic_projections=32)))

if __name__ == '__main__':
    main()
