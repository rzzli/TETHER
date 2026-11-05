"""Post-result supplemental audit; imports no producer, product or validator.

Only run against a terminal comparison. Rejection text is evidence of the first
reported check, not branch instrumentation or proof of a unique causal fault.
The frozen oracle is read, never modified. Negative findings are retained.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ARMS = ('tether', 'independent', 'hash_schema', 'reject_all')
PRINCIPAL = ('tether', 'independent')

# Bounded phrases derived from the contract and previously exposed first-run
# reasons. This is a review aid, not a second policy oracle. Unmatched reasons
# remain explicit manual-review findings; they are never silently accepted.
REASON_GROUPS = (
    ((4,), r'program.*(not available|unavailable)|unavailable program'),
    ((5, 7), r'(active/eligible|endpoint.*phase|endpoint/eligibility)'),
    ((8,), r'(program and endpoint|program/endpoint missing)'),
    ((9,), r'(eligibility.*after origin|program not yet eligible)'),
    ((10,), r'(invalid datetime|timestamp requires timezone)'),
    ((11,), r'(requires v2|unsupported case)'),
    ((12,), r'duplicate json (key|property)'),
    ((13,), r'(invalid value.*program|phase_at_origin.*scalar type)'),
    ((14,), r'unknown.?fields'),
    ((15,), r'unsupported.*packet version|unsupported evidence-packet'),
    ((16,), r'duplicate observation id'),
    ((17, 18, 57, 66), r'(source checksum mismatch|source byte mismatch)'),
    ((19,), r'(reference-only artifact|non-evidence artifact)'),
    ((20,), r'(unsupported input role|unsupported source role)'),
    ((21,), r'(missing input-lineage reference|missing source parent)'),
    ((22,), r'(input-lineage cycle|source graph cycle)'),
    ((23,), r'observation lineage escapes'),
    ((24,), r'(derived node requires computed_at|derived node computation time missing)'),
    ((40, 41, 42), r'(hypothesis derivation scope|clinical/known-drug evidence|unreviewed evidence|unqualified numerical features)'),
    ((43,), r'(outside declared range|invalid numerical feature/category/range)'),
    ((47,), r'unsupported scorer schema'),
    ((48, 49), r'(training/calibration.*(reach|origin))'),
    ((50,), r'(synthetic weights cannot score|scorer/profile mismatch)'),
    ((55,), r'(budget bounds.*nonnegative|invalid resource budget)'),
    ((56,), r'unsafe (artifact|relative) path'),
    ((60,), r'(source proof inventory differs|source proof closure differs)'),
    ((61,), r'(journal/ledger claim mismatch|journal claims differ from ledger)'),
    ((62,), r'(accounting/journal mismatch|run/journal accounting mismatch)'),
    ((63,), r'(ledger-to-feature mismatch|ledger/feature mismatch)'),
    ((64,), r'(feature-to-prediction mismatch|prediction/contributions differ)'),
    ((65,), r'(trace/output fingerprint mismatch|final trace/output mismatch)'),
    ((67,), r'(auxiliary output integrity failure|auxiliary checksum mismatch)'),
    ((68,), r'(source-to-claim fingerprint mismatch|claim/source binding mismatch)'),
    ((69,), r'(externally anchored receipt hash mismatch|external receipt anchor mismatch)'),
    ((75,), r'(replay.*request.*fingerprint|request.*fingerprint.*replay)'),
    ((77,), r'(trace hash-chain failure|journal chain mismatch)'),
    ((79, 80, 82), r'(availability bound.*receipt|download availability proof differs)'),
    ((81,), r'(receipt url differs|receipt transport identity differs)'),
    ((85,), r'(grant omits actual ancestors|grant omits ancestor)'),
    ((86,), r'(role differs from selected grant|input grant/role differs)'),
    ((87,), r'(selected frame differs|independent frame differs)'),
    ((88,), r'evaluator/unsupported grant'),
    ((89,), r'(offline execution without scorer/replay/local-model|policy path is offline without scorer/replay/local)'),
    ((90,), r'case/snapshot fingerprint differs'),
    ((91,), r'(policy projection differs|decision/projection differs)'),
    ((92,), r'(dossier projection differs|dossier presentation differs)'),
    ((98,), r'missing local model/runtime (provenance|identity)'),
    ((99,), r'invalid (bounded retrieval limits|retrieval bounds)'),
    ((100,), r'(selection cap must be|invalid selection.?cap)'),
    ((101,), r'(endpoint must be explicit.*loopback|endpoint not explicit.*loopback)'),
    ((103,), r'(local model request/payload binding mismatch|local request/payload binding mismatch)'),
    ((104,), r'(local model response/usage/selection binding mismatch|response/account/selection mismatch)'),
    ((106,), r'(successful process supervision declaration differs|unsuccessful supervision declaration)'),
    ((107,), r'(current launcher code/version differs|launcher identity differs)'),
    ((108,), r'(process timeout must be|invalid process resource bounds)'),
)
REASONS = {f'EP{number:03}': pattern for numbers, pattern in REASON_GROUPS for number in numbers}


def read(path):
    return json.loads(Path(path).read_bytes())


def pin(path):
    raw = Path(path).read_bytes()
    return dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def review_cell(record, oracle, primary):
    """Supplement primary scores; do not independently rescore observables here."""
    answer = record['result']
    expected, actual = oracle['decision'], answer.get('decision', 'missing')
    returned = record.get('disposition') == 'returned'
    require(primary['expected_decision'] == expected and primary['observed_decision'] == actual, 'Primary row decision differs from retained result/oracle')
    reason = '\n'.join(str(answer[k]) for k in ('reason', 'error') if k in answer)
    if not returned or actual in ('error', 'unsupported', 'missing'):
        cause = 'execution_or_interface_failure'
    elif expected != 'reject':
        cause = 'valid_control_observables_match' if primary['fully_conformant'] else 'valid_control_mismatch'
    elif actual != 'reject':
        cause = 'intended_rejection_not_observed'
    elif record['implementation'] not in PRINCIPAL:
        cause = 'diagnostic_control_not_full_policy_witness'
    elif oracle['control_id'] not in REASONS:
        cause = 'manual_review_unmapped_rejection'
    elif re.search(REASONS[oracle['control_id']], reason, flags=re.I | re.S):
        cause = 'first_reported_reason_matches_intended_fault'
    else:
        cause = 'manual_review_unmatched_rejection_reason'
    return dict(control_id=oracle['control_id'], implementation=record['implementation'],
        repetition=record['repetition'], expected_decision=expected, observed_decision=actual,
        disposition=record.get('disposition'), primary_fully_conformant=primary['fully_conformant'],
        primary_observable_mismatches=primary['observable_mismatches'],
        causal_review=cause, retained_reason=reason, retained_stage=answer.get('stage'),
        retained_obligations=answer.get('violated_obligations', []),
        retained_observables=answer.get('observables', {}))


def terminal_grid(frozen, execution, oracle):
    ids = [r['control_id'] for r in frozen['cases']]
    require(ids == [f'EP{n:03}' for n in range(1, 110)], 'Requires complete corrected109 case inventory')
    require(frozen['implementations'] == list(ARMS) and frozen['settings']['repetitions'] == 3, 'Unexpected schedule')
    require([r['control_id'] for r in oracle] == ids, 'Oracle inventory differs')
    require(all(r['construction_stratum'] == 'exposed_authored_construction' for r in oracle), 'Exposure differs')
    grid = {f'{cid}-r{rep}-{arm}': (cid, rep, arm) for cid in ids for rep in (1, 2, 3) for arm in ARMS}
    cells = [r['cell'] for r in execution['records']]
    require(execution['status'] == 'executed' and execution['expected_cells'] == execution['terminal_cells'] == len(grid), 'Comparison is not terminal and complete')
    require(len(cells) == len(grid) and set(cells) == set(grid), 'Missing, duplicate or unexpected terminal cells')
    require(execution['after_checks'] and all(value is True for value in execution['after_checks'].values()), 'Frozen checks failed')
    return grid


def audit(root):
    root = Path(root).resolve()
    execution = read(root / 'comparison/EXECUTION.json')  # absent/incomplete stops before any results
    frozen, oracle_doc = read(root / 'FROZEN.json'), read(root / 'oracle.json')
    oracle = {r['control_id']: r for r in oracle_doc['cases']}
    grid = terminal_grid(frozen, execution, oracle_doc['cases'])
    primary = read(root / 'ANALYSIS.json')
    primary_rows = {r['cell']: r for r in primary['rows']}
    require(primary['unique_cases'] == 109 and primary['cells'] == len(grid) and
            len(primary['rows']) == len(grid) and set(primary_rows) == set(grid), 'Primary analysis lacks complete denominator')
    require(pin(root / 'oracle.json') == frozen['oracle_pin'], 'Oracle bytes changed')
    started = read(root / 'comparison/STARTED.json')
    require(started['freeze_pin'] == pin(root / 'FROZEN.json'), 'Freeze anchor changed')
    require(started['checks'] and all(v is True for v in started['checks'].values()), 'Failed execution preconditions')
    # Connect the causal input review to exactly the frozen bytes. Full runtime/
    # source closure reconstruction remains a separate, mandatory release check.
    actual_bundles = {p.relative_to(root / 'bundles').as_posix(): pin(p)
        for p in (root / 'bundles').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    require(actual_bundles == frozen['bundles'], 'Frozen bundles changed')
    require(sorted(p.relative_to(root / 'bundles').as_posix() for p in (root / 'bundles').rglob('*')
        if p.is_dir() and '__pycache__' not in p.parts) == sorted(frozen['bundle_directories']), 'Frozen directory shape changed')
    rows, pins = [], []
    for ref in execution['records']:
        cell = root / 'comparison' / ref['cell']
        require(pin(cell / 'RESULT.json') == {k: ref[k] for k in ('sha256', 'bytes')}, 'Terminal record changed')
        record = read(cell / 'RESULT.json')
        require((record['control_id'], record['repetition'], record['implementation']) == grid[ref['cell']], 'Cell identity mismatch')
        require(pin(cell / 'stdout.json') == record['stdout_pin'] and pin(cell / 'stderr.txt') == record['stderr_pin'], 'Worker streams changed')
        if record['disposition'] == 'returned':
            stdout = read(cell / 'stdout.json')
            require(stdout['implementation'] == record['implementation'] and stdout['schema_version'] == 1, 'Worker identity differs')
            require(stdout['result']['control_id'] == record['control_id'] and stdout['result'] == record['result'], 'Raw result differs from terminal record')
        rows.append(dict(cell=ref['cell'], **review_cell(record, oracle[record['control_id']], primary_rows[ref['cell']])))
        pins.append(dict(cell=ref['cell'], result=pin(cell / 'RESULT.json'), stdout=record['stdout_pin'], stderr=record['stderr_pin']))
    ready_witnesses = {}
    for cid in ('EP072', 'EP097'):
        events = [json.loads(line) for line in (root / 'bundles' / cid / 'run/trace.jsonl').read_bytes().splitlines()]
        plan = next(e['details'] for e in events if e['event'] == 'plan')
        ready = [s['category'] for s in plan['steps'] if s['initial_status'] == 'ready']
        ready_witnesses[cid] = dict(ready_categories=ready, eligible_later_category_present='perturbation' in ready,
            result_rows=[r for r in rows if r['control_id'] == cid and r['implementation'] in PRINCIPAL])
        require(ready == ['genetics', 'perturbation'], 'Later-work causal control is vacuous')
    findings = [r for r in rows if r['implementation'] in PRINCIPAL and
        (not r['primary_fully_conformant'] or r['causal_review'].startswith('manual_review') or r['causal_review'] == 'execution_or_interface_failure')]
    special = {cid: [r for r in rows if r['control_id'] == cid] for cid in ('EP023', 'EP072', 'EP075', 'EP077', 'EP097', 'EP109')}
    return dict(schema_version=1, status='AUDIT_COMPLETE_WITH_FINDINGS' if findings else 'AUDIT_COMPLETE_NO_FLAGGED_PRINCIPAL_MISMATCH',
        reviewed_at_utc=datetime.now(timezone.utc).isoformat(), run=str(root), runtime_versions=frozen['runtime_versions'],
        counts=dict(cases=109, arms=4, repetitions=3, scheduled_cells=1308, reviewed_cells=len(rows)),
        pins={name: pin(root / name) for name in ('FROZEN.json', 'oracle.json', 'ANALYSIS.json', 'comparison/STARTED.json', 'comparison/EXECUTION.json')},
        checker_pin=pin(__file__), primary_totals=primary['totals'], special_controls=special, later_work_witnesses=ready_witnesses,
        principal_findings=findings, rows=rows, reviewed_stream_pins=pins,
        limits=['All109 cases are exposed authored constructions; repeated cells are not independent samples.',
            'EP001 and EP025 are two policy views of the same construction.',
            'Matching first rejection text is not branch instrumentation or an isolated-check ablation.',
            'Archive scheduler traces describe retained fictional executions; no live-model performance claim.',
            'Observable scores are copied from pinned primary analysis, not independently recomputed by this helper.',
            'Independent reconstruction, valid-neighbor review and resource audit remain separate requirements.',
            'Diagnostic hash/schema and reject-all controls do not claim full-policy causal coverage.',
            'False admissions are relative to the frozen policy; source integrity does not imply scientific truth.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(args.output.resolve().is_relative_to(Path(__file__).resolve().parent), 'Write only in postresult evidence directory')
    require(not args.output.exists(), 'Never overwrite a previous review')
    result = audit(args.run)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], counts=result['counts'],
        findings=len(result['principal_findings']), output=str(args.output), output_pin=pin(args.output)), indent=2))


if __name__ == '__main__':
    main()
