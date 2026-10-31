"""Retain exact source/AST delta and existing pure-proof bindings; no test replay."""
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'CAPTURED-ARCHIVE-CHECKER-FREEZE-v3.json'

def pin(name):
    path = HERE / name
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def dump(value):
    return ast.dump(value, include_attributes=False)

def main():
    assert not OUT.exists(), 'Preserve first retention'
    old = (HERE/'captured_archive_v2.py').read_text(encoding='utf-8')
    new = (HERE/'captured_archive_v3.py').read_text(encoding='utf-8')
    changes = [
        ('Captured native-v7 archive v2: callback and one-line marker corrections.',
         'Captured native-v7 archive v3: source-null and numeric-boundary corrections.'),
        ('def _number(v):return type(v) in (int,float) and math.isfinite(v) and v>=0',
         'def _number(v):return (type(v) is int and v>=0) or (type(v) is float and math.isfinite(v) and v>=0)'),
        ("            for key in ('closed_before','close_attempted','close_return_observed','close_success','closed_after'):\n                if key in outcome:_need(type(outcome[key]) is bool,'cleanup_outcome_bool')",
         "            for key in ('closed_before','close_attempted','close_return_observed','closed_after'):\n                if key in outcome:_need(type(outcome[key]) is bool,'cleanup_outcome_bool')\n            if 'close_success' in outcome:\n                if outcome['close_success'] is None:\n                    _need(outcome.get('closed_before') is True and outcome.get('close_attempted') is False and outcome.get('close_return_observed') is False and outcome.get('closed_after') is True and outcome.get('close_error') is None,'cleanup_unattempted_close_null')\n                else:_need(type(outcome['close_success']) is bool,'cleanup_outcome_bool')"),
    ]
    transformed = old
    for before, after in changes:
        assert transformed.count(before) == 1
        transformed = transformed.replace(before, after, 1)
    assert transformed == new
    old_nodes, new_nodes = ast.parse(old).body, ast.parse(new).body
    assert len(old_nodes) == len(new_nodes)
    changed, unchanged = [], []
    for index, (left, right) in enumerate(zip(old_nodes, new_nodes)):
        label = getattr(left, 'name', f'top_level_{index}')
        (unchanged if dump(left) == dump(right) else changed).append(label)
    assert changed == ['top_level_0', '_number', '_run_graph']
    for name in ('_Analysis', 'check_archive'):
        left = next(node for node in old_nodes if getattr(node, 'name', None) == name)
        right = next(node for node in new_nodes if getattr(node, 'name', None) == name)
        assert dump(left) == dump(right)
    proof = json.loads((HERE/'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v3.json').read_text(encoding='utf-8'))
    assert proof['status'] == 'passed' and proof['methods'] == 13 and proof['inputs_unchanged'] is True
    assert len(proof['frozen_case_results']) == 32 and len(proof['focused_before_after']) == 2
    assert not proof['failures'] and not proof['errors']
    assert proof['inputs']['captured_archive_v3.py'] == pin('captured_archive_v3.py')
    assert proof['checker'] == pin('check_captured_archive_v3.py')
    names = [
        'ARCHIVE-CHECKER-CORRECTION-ROOT-DECISION-v3.json',
        'CAPTURED-NATIVE-ARCHIVE-CONTRACT-v3.json',
        'CAPTURED-NATIVE-ARCHIVE-FIXTURES-v3.json',
        'CAPTURED-NATIVE-ARCHIVE-FIXTURE-FREEZE-v3.json',
        'captured_archive_v2.py', 'check_captured_archive_v2.py',
        'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v2.json',
        'CAPTURED-ARCHIVE-CHECKER-FREEZE-v2.json',
        'CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PEER-v2.json',
        'CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PROBES-v3.json',
        'captured_archive_v3.py', 'check_captured_archive_v3.py',
        'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v3.json',
        'CAPTURED-ARCHIVE-EFFECTIVE-V3-v2.md', 'CAPTURED-ARCHIVE-EFFECTIVE-V3-v3.md',
        'prepare_archive_checker_correction_v3.py', Path(__file__).name,
    ]
    value = dict(
        schema_version=1, status='frozen_source_pure_candidate_for_independent_review',
        recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        inputs={name:pin(name) for name in names},
        exact_byte_transform_matches=True, replacement_count=len(changes),
        changed_top_level_ASTs=changed, unchanged_top_level_ASTs=unchanged,
        callback_and_LF_analysis_and_entry_ASTs_unchanged=True,
        methods=13, frozen_synthetic_projections=32, fully_rebound_before_after=2,
        correction_scope=['Source-valid already-closed nullable close result; no fabricated close observation.',
                          'Noncoercing exact integer/finite-float predicate; periodic range rejects giant integer.'],
        checker_or_tests_rerun_for_this_record=False,
        actual_old_archive_capture_or_replay=False, SDK_OS_native_model_operations=0,
        CPU_GGUF_oldpack_reads=0, cleanup_qualification_expanded=False,
        profile_qualified=False, originals_authenticated=False,
        actual_directory_complete=False, source_qualified=False,
        independent_peer_acceptance=False,
    )
    with OUT.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(value, handle, sort_keys=True, indent=2)
        handle.write('\n')
    print(json.dumps(dict(record=pin(OUT.name), methods=13, frozen_synthetic_projections=32)))

if __name__ == '__main__':
    main()
