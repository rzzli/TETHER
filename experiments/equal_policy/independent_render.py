"""Independent deterministic dossier text reconstruction from retained fields.

Literal wording is a versioned presentation contract. No product renderer is
imported or executed; scientific claims are not invented or paraphrased.
"""
from .independent import canonical


def render_dossier(case, snapshot, run, claims, prediction):
    h, p = case['hypothesis'], prediction
    lines = [f"# AsOf dossier: {case['case_id']}", '',
        f"Target: {h['target_id']}; indication: {h['indication_id']}.",
        f"Intended action: {h['intended_action']}; modality: {h['modality']}; tissue: {h['tissue'] or 'unspecified'}.",
        f"Origin: {case['origin']}; profile: {run['profile']}; task: {case['task']}.",
        f"Workflow: {run['status']}; backend: {run['backend_id']}.", '']
    if snapshot['coverage'].get('interpretation_scope') == 'resource_annotation_only':
        lines.extend(['## Evidence relevance and hypothesis limits', '',
            'Resource annotation support: source-linked target/disease records are reproduced. '
            'Therapeutic relevance: not assessed for the intended action, modality, population or regimen. '
            'A literature mention, genetic association or provider score does not establish intervention efficacy.', '',
            'Clinical outcomes and reviewer judgments remain evaluator-only. No disease subtype was inferred '
            'and this hypothesis has not been refined.', '',
            '| Unresolved qualification | Value |', '| --- | --- |'])
        for name, qualification in snapshot['coverage'].get('hypothesis_qualification', {}).items():
            lines.append(f"| {name.replace('_', ' ')} | {qualification['value'] or 'unspecified'} |")
        lines.append('')
    if p['synthetic']:
        lines.extend(['**Synthetic demonstration: the weights and observations are fixtures. '
                      'This number is not a scientific prediction.**', ''])
    if p['probability'] is None:
        lines.extend([f"Probability withheld: {p['reason']}.", ''])
    else:
        lines.extend([f"Probability of {p['endpoint']} within {p['horizon_months']} months: {p['probability']:.4f}.",
            f"Scorer: {p['scorer_id']}; calibration: {p['calibration']}; model-feature coverage: {p['feature_coverage']:.1%}.", ''])
    if p['contributions']:
        lines.extend(['## Frozen scorer contributions', '',
            'Contributions are in log odds and describe the predictor, not biological causality.', '',
            '| Feature | Value | Coefficient | Contribution | Imputed |', '| --- | ---: | ---: | ---: | --- |'])
        for name, item in p['contributions'].items():
            lines.append(f"| {name} | {item['value']:.4g} | {item['coefficient']:.4g} | {item['log_odds']:.4g} | {item['imputed']} |")
        lines.extend([f"\nIntercept: {p['intercept']:.4g}.", ''])
    lines.extend(['## Grounded claims', '',
        'Statements below are copied from the approved normalized records. Citation '
        'grounding does not establish that a source interpretation or method is scientifically correct.', ''])
    for claim in claims:
        o, c = claim['evidence']['observation'], claim['evidence']['citation']
        lines.extend([f"### {claim['claim_id']} ({claim['specialist']})", '', '> ' + o['statement'].replace('\n', '\n> '), '',
            f"Interpretation: {o['polarity']}; direction: {o['mechanism_direction']}. Dependency group: {o['dependency_group']}; declared QC: {o['method']['qc_status']}.",
            f"Source: {c['dataset_id']}/{c['release_id']}; artifact {c['artifact_id']}; observation {o['observation_id']}.",
            f"SHA-256: `{c['artifact_sha256']}`.", ''])
        if o['method']['limitations']:
            lines.extend(['Limitations: ' + '; '.join(o['method']['limitations']) + '.', ''])
        if o['source_metrics']:
            lines.extend(['Provider metrics (descriptive): `' + canonical(o['source_metrics']).decode('utf-8') + '`.', ''])
        if o['missingness']:
            lines.extend(['Unknown fields: ' + '; '.join(f'{key}: {value}' for key, value in o['missingness'].items()) + '.', ''])
    if not claims:
        lines.extend(['No approved observed claims were selected.', ''])
    lines.extend(['## Coverage and exclusions', '', '| Specialist | Run status | Available | Selected |', '| --- | --- | ---: | ---: |'])
    for category, coverage in run['coverage'].items():
        lines.append(f"| {category} | {coverage['status']} | {coverage['available_observations']} | {coverage['selected_observations']} |")
    for category, coverage in run['coverage'].items():
        for record in coverage['nonobserved']:
            lines.append(f"\n{category}: {record['status']} ({record['observation_id']}): {record['reason']}")
    for exclusion in run['exclusions']:
        lines.append(f"\nExcluded {exclusion['level']} {exclusion['item_id']}: {exclusion['reason']}.")
    if snapshot['coverage']:
        lines.extend(['', 'Source coverage: `' + canonical(snapshot['coverage']).decode('utf-8') + '`.'])
    usage, measured, estimated = run['usage'], run['measured_usage'], run['estimated_usage']
    lines.extend(['', f"Calls: {run['calls']}; accounted cost: ${usage['cost_usd']:.4f}; input/output tokens: {usage['input_tokens']}/{usage['output_tokens']}.", '',
        f"Measured cost: ${measured['cost_usd']:.4f}; conservatively estimated upper cost: ${estimated['cost_usd']:.4f}.", '',
        'No live model provider or scientific computation is invoked by the default backend. '
        "Historical retrieval controls do not certify a model's training cutoff or knowledge. "
        'OS-level isolation is required before running arbitrary agents on locked benchmarks.', ''])
    return '\n'.join(lines).encode('utf-8')
