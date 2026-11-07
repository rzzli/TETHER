"""Prepare evaluator-only, unanswered development forms from the retained source audit."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

from tether_engine.artifacts import read_ledger_json
from tether_engine.contracts import Case
from tether_engine.maintenance import write_new_json
from tether_engine.serde import ContractError, decode, read_json, safe_child, sha256_file


def prepare(project: Path, output: Path):
    project, output = project.resolve(), output.resolve()
    if not output.is_relative_to(project/'data/benchmark/gold_evidence'):
        raise ContractError('Review forms must remain in evaluator-only gold_evidence storage')
    if output.exists():
        raise ContractError('Review directory exists; preserve previous forms')
    registry = read_json(project/'planning/run-registry.json')
    entries = [row for row in registry['entries'] if row['id'] == registry['canonical_pilot_id']]
    if len(entries) != 1 or entries[0]['state'] != 'canonical':
        raise ContractError('Canonical pilot missing or ambiguous')
    entry = entries[0]
    for ref in entry['reports']:
        if sha256_file(safe_child(project, ref['path'])) != ref['sha256']:
            raise ContractError('Registered report changed')
    audit_ref = next(ref for ref in entry['reports'] if Path(ref['path']).name == 'source-review.json')
    audit = read_json(safe_child(project, audit_ref['path']))
    forms = []
    for record in entry['cases']:
        run = safe_child(project, record['path'])
        if sha256_file(run/'receipt.json') != record['receipt_sha256']:
            raise ContractError('Run receipt anchor mismatch')
        receipt = read_json(run/'receipt.json')
        for name in ('inputs.json', 'ledger.json', 'run.json', 'dossier.md'):
            if sha256_file(run/name) != receipt['outputs'][name]:
                raise ContractError('Reviewed run bytes changed')
        case = decode(Case, read_json(run/'inputs.json')['case'])
        rows = [row for row in audit['rows'] if row['case_id'] == case.case_id]
        claims = {claim['claim_id']: claim for claim in read_ledger_json(run/'ledger.json')['claims']}
        selected = []
        for row in rows:
            claim = claims[row['claim_id']]
            observation = claim['evidence']['observation']
            locator = observation['source_locator']
            if (observation['observation_id'] != row['observation_id'] or
                observation['statement'] != row['statement'] or
                any(locator[key] != row[key] for key in ('source_id', 'row_group', 'row'))):
                raise ContractError('Audit row differs from sealed claim')
            selected.append({'claim': claim, 'original_reference': {
                key: row[key] for key in ('source_path', 'source_sha256', 'row_group', 'row')},
                'assessment': dict.fromkeys(('source_support', 'action_modality_relevance',
                    'context_correctness', 'method_correctness', 'error_severity',
                    'missingness_handling', 'rationale', 'additional_source_references'))})
        if len(selected) < 2:
            raise ContractError('At least two retained audit rows required per development case')
        coverage = read_json(run/'run.json')['coverage']
        forms.append({'schema_version': 1, 'role': 'evaluation_only', 'status': 'unreviewed',
            'case': case, 'hypothesis_fingerprint': case.hypothesis.key,
            'run_receipt_sha256': record['receipt_sha256'],
            'source_audit_sha256': audit_ref['sha256'],
            'selection_policy': 'Existing technical-audit rows; purposive development sample; not representative or blinded',
            'available_observations_by_category': {key: value['available_observations'] for key, value in coverage.items()},
            'reviewer': None, 'reviewed_at': None, 'claims': selected,
            'case_assessment': dict.fromkeys(('major_omissions', 'dossier_utility', 'review_minutes',
                'disagreements', 'adjudicator', 'adjudication_status', 'notes'))})
        del claims
    if len(forms) != 10 or len({form['case'].case_id for form in forms}) != 10:
        raise ContractError('Expected ten distinct development hypotheses')
    output.mkdir(parents=True, exist_ok=False)
    index = ['# T6 expert development review', '',
        'Unreviewed forms, not gold answers. This is an unblinded development review of the offline extractor.',
        'These purposively selected source-audit rows cannot estimate whole-dossier accuracy or clinical validity.',
        'Complete independent copies for each reviewer. Keep original templates unchanged and retain disagreements.',
        'Use supported / contradicted / not_assessable for source support; explain every judgment.',
        'Review source context and action/modality relevance separately. Null means unanswered, not no error.',
        'Clinical probabilities remain null. Provider scores are descriptive, not causal effect sizes.',
        'The full dossier and source files stay local; do not treat this package as clearance to redistribute source data.', '']
    files = []
    for record, form in zip(entry['cases'], forms):
        case_id = form['case'].case_id
        filename = case_id+'.json'
        write_new_json(output/filename, form)
        files.append({'case_id': case_id, 'path': filename, 'sha256': sha256_file(output/filename),
                      'selected_claims': len(form['claims'])})
        hypothesis = form['case'].hypothesis
        index.extend([f'## {case_id}', '',
            f'Action: {hypothesis.intended_action}; modality: {hypothesis.modality}; tissue: unspecified.',
            f'[Blank assessment form]({filename}) · [Complete local dossier]({(project/record["path"]/"dossier.md").as_posix()})', ''])
        for item in form['claims']:
            claim = item['claim']
            index.extend([f'**{claim["claim_id"]} ({claim["specialist"]})**', '',
                          claim['evidence']['observation']['statement'], ''])
    (output/'README.md').write_text('\n'.join(index)+'\n', encoding='utf-8')
    manifest = {'schema_version': 1, 'role': 'evaluation_only', 'status': 'prepared_unreviewed',
        'created_at_utc': datetime.now(timezone.utc), 'canonical_pilot_id': entry['id'],
        'source_audit_sha256': audit_ref['sha256'], 'reviewed_cases': 0,
        'scientific_adjudication': 'not_run', 'files': files, 'readme_sha256': sha256_file(output/'README.md')}
    write_new_json(output/'manifest.json', manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.project_root, args.output)
    print(f"Prepared {len(result['files'])} unreviewed cases; scientific adjudication not run")


if __name__ == '__main__':
    main()
