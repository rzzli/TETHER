"""Evaluator-side panel integrity checks, separate from scientific correctness.

Fresh contexts are procedural separation, not independent error distributions.
This module never supplies answers or references to a model-backed workflow.
"""
from datetime import date
import hashlib
from pathlib import Path

from tether_engine.serde import (ContractError, MAX_NORMALIZED_JSON_BYTES, fingerprint, parse_json,
                        read_json, safe_child, sha256_file)


SCOPE = ('symbol', 'disease_id', 'intended_action', 'modality')
DEPTHS = {'full_text', 'fulltext', 'abstract', 'abstract_only', 'metadata', 'metadata_only',
          'official_summary', 'official_label', 'official_release', 'registry_record'}
RUBRIC = {'source_fidelity', 'identity_disease_relevance', 'action_relevance',
          'modality_relevance', 'context_transferability', 'interpretation_risk'}


def read_bound_json(path, expected=None):
    """Fingerprint the very bytes parsed, with the ordinary normalized size cap."""
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_NORMALIZED_JSON_BYTES + 1)
    if len(raw) > MAX_NORMALIZED_JSON_BYTES:
        raise ContractError('Scientific reference JSON exceeds normalized size limit')
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ContractError('Scientific reference bytes differ from frozen fingerprint')
    return parse_json(raw), digest


def validate_panel(panel, case_pack, *, cutoff='2026-10-18'):
    """Require complete scoped questions and resolvable primary-source references.

    Passing means an inspectable blinded assessment exists; no source assertion is
    certified true merely because its citation resolves inside this JSON document.
    """
    if panel.get('schema_version') != 1 or panel.get('reviewer_type') != 'ai_agent':
        raise ContractError('Unsupported reference panel provenance')
    if (panel.get('blind_to_arm_outputs') is not True or
            panel.get('other_reviewer_answers_visible') is not False):
        raise ContractError('Initial reference review was not procedurally blinded')
    provenance = panel.get('model_provenance', {})
    if not provenance.get('execution_id') or (provenance.get('model_id') is None and not provenance.get('reason')):
        raise ContractError('Unknown model identity needs an explicit reason and execution identity')
    wanted = {c['case_id']: c for c in case_pack['cases']}
    rows = panel.get('cases', [])
    if len(rows) != len(wanted) or {c.get('case_id') for c in rows} != set(wanted):
        raise ContractError('Panel must cover each frozen hypothesis exactly once')
    sources, questions = 0, 0
    for row in rows:
        expected = wanted[row['case_id']]
        if (row.get('case_key') != row['case_id'] or any(row.get(k) != expected[k] for k in SCOPE) or
                row.get('tissue') != expected.get('tissue')):
            raise ContractError('Panel changed a frozen hypothesis scope')
        if row.get('reference_level') not in ('ai_source_adjudicated', 'unreviewed'):
            raise ContractError('AI panel cannot claim external scientific independence')
        if 'context_constraints' not in row or 'uncertainties' not in row:
            raise ContractError('Missing interpretation constraints')
        refs = row.get('primary_sources', [])
        ids = [r.get('source_id') for r in refs]
        urls = [r.get('url') for r in refs]
        if (len(refs) < 2 or len(set(ids)) != len(ids) or
                len(set(urls)) != len(urls) or any(not v for v in ids)):
            raise ContractError('Require distinct inspectable primary references per case')
        for ref in refs:
            if not str(ref.get('url', '')).startswith('https://') or not ref.get('title'):
                raise ContractError('Missing primary reference URL or title')
            if ref.get('access_depth') not in DEPTHS:
                raise ContractError('Unknown source access depth')
            if not ref.get('source_type') or not ref.get('findings_supported'):
                raise ContractError('Primary reference does not identify its supported findings')
            published = ref.get('publication_date')
            if published is not None:
                try:
                    # Year/month precision is acceptable, and stays explicit.
                    parsed = date.fromisoformat(published + '-01' * (2 - published.count('-')))
                except (ValueError, TypeError, AttributeError) as error:
                    raise ContractError('Invalid primary reference publication date') from error
                if parsed > date.fromisoformat(cutoff):
                    raise ContractError('Future primary reference is ineligible')
            elif not ref.get('publication_date_reason'):
                raise ContractError('Unknown publication date needs an explanation')
        entries = row.get('questions', [])
        qids = [q.get('question_id') for q in entries]
        if len(qids) != len(set(qids)) or not {'Q2', 'Q3', 'Q4'} <= set(qids) or set(qids) - {'Q1', 'Q2', 'Q3', 'Q4'}:
            raise ContractError('Missing or duplicate reference questions')
        for question in entries:
            if question['question_id'] == 'Q1' and question.get('finding') == 'pending_original_rows':
                continue
            if not question.get('finding') or not question.get('rationale') or 'uncertainty' not in question:
                raise ContractError('Question lacks a qualified interpretation')
            if not question.get('source_refs') or set(question['source_refs']) - set(ids):
                raise ContractError('Question citation does not resolve')
            questions += 1
        sources += len(refs)
    return {'status': 'initial_panel_contract_valid', 'cases': len(rows),
            'primary_references': sources, 'answered_questions': questions,
            'external_scientific_validation': False,
            'source_factual_correctness': 'requires_source_adjudication'}


def seal_panels(case_pack_path, panel_paths, output):
    """Seal initial answers before an adjudicator sees either reviewer."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    pack, pack_sha256 = read_bound_json(case_pack_path)
    panels, ids, executions = [], set(), set()
    for path in panel_paths:
        panel, panel_sha256 = read_bound_json(path)
        report = validate_panel(panel, pack)
        reviewer, execution = panel['reviewer_id'], panel['model_provenance']['execution_id']
        if reviewer in ids or execution in executions:
            raise ContractError('Two reviewer labels cannot conceal a shared execution')
        ids.add(reviewer); executions.add(execution)
        if sha256_file(path) != panel_sha256:
            raise ContractError('Initial panel changed during validation')
        panels.append({'path': str(Path(path).resolve()), 'sha256': panel_sha256, 'validation': report})
    if len(panels) != 2:
        raise ContractError('Exactly two initial reference panels are required')
    report = {'schema_version': 1, 'role': 'evaluation_only',
              'case_pack_sha256': pack_sha256, 'panels': panels,
              'status': 'sealed_before_adjudication', 'external_independence': False}
    with output.open('x', encoding='utf-8') as stream:
        import json
        json.dump(report, stream, indent=2); stream.write('\n')
    return report


def validate_q1_rows(supplement, expected_rows, report_sha256):
    """Match every independently reviewed row to its frozen audited identity."""
    if (supplement.get('blind_to_arm_outputs') is not True or
            supplement.get('other_reviewer_answers_visible') is not False or
            supplement.get('source_report_sha256') != report_sha256):
        raise ContractError('Q1 review blinding or source version mismatch')
    if not supplement.get('reviewer_id') or not supplement.get('model_provenance'):
        raise ContractError('Q1 review lacks reviewer provenance')
    model = supplement['model_provenance']
    if not model.get('execution_id') or (model.get('model_id') is None and not model.get('reason')):
        raise ContractError('Q1 review lacks an execution identity or unknown-model explanation')
    cases = supplement.get('cases', [])
    if len(cases) != len(expected_rows) or {c.get('case_id') for c in cases} != set(expected_rows):
        raise ContractError('Q1 supplement must cover every frozen case exactly once')
    count, answers = 0, {}
    for case in cases:
        if case.get('question_id') != 'Q1' or not case.get('finding') or not case.get('rationale') or 'uncertainty' not in case:
            raise ContractError('Incomplete Q1 case assessment')
        expected = expected_rows[case['case_id']]
        observations = case.get('observations', [])
        if len(observations) != len(expected) or {r.get('observation_id') for r in observations} != set(expected):
            raise ContractError('Q1 row missing, duplicated or added outside selection')
        for row in observations:
            if row.get('source_row_sha256') != expected[row['observation_id']]:
                raise ContractError('Q1 review refers to changed original source content')
            if row.get('answer') not in ('supported','contradicted','uncertain','unavailable') or not row.get('rationale'):
                raise ContractError('Q1 source answer lacks qualification')
            rubric = row.get('rubric', {})
            if set(rubric) != RUBRIC or any(not isinstance(v,str) or not v.strip() for v in rubric.values()):
                raise ContractError('Q1 requires all six explanatory rubric axes')
            if 'context_qualifiers' not in row:
                raise ContractError('Q1 context limits must be explicit')
            answers[row['answer']] = answers.get(row['answer'],0) + 1
            count += 1
    return {'status':'q1_contract_valid','cases':len(cases),'reviewed_rows':count,
            'answers':answers,'external_scientific_validation':False}


def validate_q1(supplement, source_root, expected_report_sha256):
    source_root = Path(source_root)
    path = source_root/'reference-report.json'
    if sha256_file(path) != expected_report_sha256:
        raise ContractError('Q1 frozen source report bytes differ')
    report = read_json(path)
    expected = {}
    for case in report['cases']:
        root = safe_child(source_root, case['case_id'])
        context_path = root/'reference-context.json'
        if sha256_file(context_path) != case['reference_context_sha256']:
            raise ContractError('Q1 source context bytes differ')
        context = read_json(context_path)
        for name,key in (('source-packet.json','source_packet_sha256'),('raw-row-audit.json','raw_row_audit_sha256')):
            if sha256_file(root/name) != context[key]:
                raise ContractError('Q1 selected packet or raw audit bytes differ')
        audits = read_json(root/'raw-row-audit.json')
        indexed = {r['observation_id']:r['source_row_sha256'] for r in audits}
        if len(indexed) != len(audits) or any(fingerprint(r['projected_original_row']) != r['source_row_sha256'] for r in audits):
            raise ContractError('Q1 raw projection identity is inconsistent')
        packet = read_json(root/'source-packet.json')['observations']
        if (len(packet) != len(indexed) or {r['observation_id'] for r in packet} != set(indexed) or
                any(r['method']['parameters']['source_row_sha256'] != indexed[r['observation_id']] for r in packet)):
            raise ContractError('Q1 normalized and original row identities differ')
        expected[case['case_id']] = indexed
    return validate_q1_rows(supplement, expected, expected_report_sha256)
