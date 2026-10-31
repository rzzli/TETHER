"""Retain root source-only correction scope, then make new versioned sources."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DECISION = HERE / 'ARCHIVE-CHECKER-CORRECTION-ROOT-DECISION-v3.json'

def pin(name):
    path = HERE / name
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def main():
    paths = [DECISION, HERE/'captured_archive_v3.py', HERE/'check_captured_archive_v3.py']
    assert all(not path.exists() for path in paths), 'Preserve all prior versions'
    assert pin('captured_archive_v2.py')['sha256'] == '380d4b7ae68d3e2bef1f519b62f47a226c542feb98d9937d95eac1d487d912e2'
    assert pin('CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PEER-v2.json')['sha256'] == '1a48b0e0e19ed873fb99c19f3a7d865f3243168cdc8831a8a598844b38f513de'
    record = dict(
        schema_version=1, recorded_at_utc=datetime.now(timezone.utc).isoformat(),
        authorization_basis='Delivered root NEW_TASK: resume narrow captured archive checker v3 correction; source/pure only.',
        required_changes=['Admit source-valid already-closed close_success JSONnull without fabricating a close return.',
                          'Use exact numeric type/range predicates without coercing huge integers through math.isfinite.',
                          'Preserve v2 callback identity and one-LF corrections; no broad outer catch.'],
        required_evidence='Fully rebound synthetic before/after cases, all32 frozen projections, callback OverflowError identity, and unchanged qualification scope.',
        preserved={name:pin(name) for name in [
            'captured_archive_v2.py', 'check_captured_archive_v2.py',
            'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v2.json',
            'CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PROBES-v3.json',
            'CAPTURED-NATIVE-ARCHIVE-INDEPENDENT-PEER-v2.json',
            'CAPTURED-ARCHIVE-CHECKER-FREEZE-v2.json']},
        implementation_scope='Pure captured bytes/declarations only; no fileport, actual old archive replay, old payload, SDK/native/API/model/CPU/pack operation.',
        source_qualified=False, profile_qualified=False, execution_authorized=False,
    )
    with DECISION.open('x', encoding='utf-8', newline='\n') as handle:
        json.dump(record, handle, sort_keys=True, indent=2)
        handle.write('\n')
    source = (HERE/'captured_archive_v2.py').read_text(encoding='utf-8')
    changes = [
        ('Captured native-v7 archive v2: callback and one-line marker corrections.',
         'Captured native-v7 archive v3: source-null and numeric-boundary corrections.'),
        ('def _number(v):return type(v) in (int,float) and math.isfinite(v) and v>=0',
         'def _number(v):return (type(v) is int and v>=0) or (type(v) is float and math.isfinite(v) and v>=0)'),
        ("            for key in ('closed_before','close_attempted','close_return_observed','close_success','closed_after'):\n                if key in outcome:_need(type(outcome[key]) is bool,'cleanup_outcome_bool')",
         "            for key in ('closed_before','close_attempted','close_return_observed','closed_after'):\n                if key in outcome:_need(type(outcome[key]) is bool,'cleanup_outcome_bool')\n            if 'close_success' in outcome:\n                if outcome['close_success'] is None:\n                    _need(outcome.get('closed_before') is True and outcome.get('close_attempted') is False and outcome.get('close_return_observed') is False and outcome.get('closed_after') is True and outcome.get('close_error') is None,'cleanup_unattempted_close_null')\n                else:_need(type(outcome['close_success']) is bool,'cleanup_outcome_bool')"),
    ]
    for before, after in changes:
        assert source.count(before) == 1
        source = source.replace(before, after, 1)
    with (HERE/'captured_archive_v3.py').open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(source)
    checker = (HERE/'check_captured_archive_v2.py').read_text(encoding='utf-8')
    checker = checker.replace("SOURCE=HERE/'captured_archive_v2.py'", "SOURCE=HERE/'captured_archive_v3.py'")
    checker = checker.replace("PROOF=HERE/'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v2.json'", "PROOF=HERE/'CAPTURED-NATIVE-ARCHIVE-SOURCE-PURE-PROOF-v3.json'")
    with (HERE/'check_captured_archive_v3.py').open('x', encoding='utf-8', newline='\n') as handle:
        handle.write(checker)
    print(json.dumps(dict(decision=pin(DECISION.name), source=pin('captured_archive_v3.py'), checker_draft=pin('check_captured_archive_v3.py'))))

if __name__ == '__main__':
    main()
