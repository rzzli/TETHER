"""Render authored, qualified clinical-development notes with source receipt checks."""
from collections import Counter
import argparse
import hashlib
import html
import json
from pathlib import Path


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def render(root, origin, output, timeline=None):
    notes = load(root / 'review-notes.json')
    cases = load(origin / 'selected.json')
    if {r['candidate_id'] for r in notes['cases']} != {r['candidate_id'] for r in cases} or len(notes['cases']) != len(cases):
        raise ValueError('Review does not cover exactly the frozen cases')
    sources = {}
    for folder in ('primary-source-receipts', 'supplemental-source-receipts'):
        for row in load(root / folder / 'index.json'):
            if row['source_id'] in sources:
                raise ValueError('Duplicate source ID')
            body = root / folder / (row['source_id'] + '.body')
            if row['status'].startswith('retrieved') and (not row.get('sha256') or not body.is_file()):
                raise ValueError('Retained source proof missing')
            if body.exists() and hashlib.sha256(body.read_bytes()).hexdigest() != row['sha256']:
                raise ValueError('Retained source bytes changed')
            sources[row['source_id']] = {**row, 'local_body': str(body) if body.exists() else None,
                'index_sha256': hashlib.sha256((root / folder / 'index.json').read_bytes()).hexdigest()}
    for item in notes['cases']:
        if not set(item['source_ids']) <= sources.keys():
            raise ValueError('Unresolved source reference')
    protocol = load(root / 'outcome-protocol.json')
    if hashlib.sha256((origin / 'selected.json').read_bytes()).hexdigest() != protocol['selection_sha256']:
        raise ValueError('Frozen selection changed')
    content_hash = None
    content_path = root / 'source-content-review.json'
    if content_path.exists():
        content = load(content_path)
        rows = content['sources']
        if (content['review_notes_sha256'] != hashlib.sha256((root / 'review-notes.json').read_bytes()).hexdigest()
            or len(rows) != len(sources) or {r['source_id'] for r in rows} != set(sources)):
            raise ValueError('Content qualification notes/source set differs')
        for row in rows:
            source = sources[row['source_id']]
            if (row['body_sha256'] != source.get('sha256') or row['index_sha256'] != source['index_sha256']
                or not isinstance(row['display_label'], str) or not row['display_label'].strip()):
                raise ValueError('Content qualification source proof differs')
            source['display_label'] = row['display_label']
        content_hash = hashlib.sha256(content_path.read_bytes()).hexdigest()
    timeline_index = {}
    timeline_hash = None
    if timeline is not None:
        from tools.feasibility.verify_intermediate_aact import verify_seal
        proof = timeline / 'evidence-manifest.json'
        paths = verify_seal(proof, hashlib.sha256(proof.read_bytes()).hexdigest())
        timeline_path = timeline / 'timeline.json'
        if timeline_path.resolve() not in paths:
            raise ValueError('Timeline omitted from seal')
        observed = load(timeline_path)
        timeline_index = {r['candidate_id']: r for r in observed}
        if len(observed) != len(cases) or set(timeline_index) != {c['candidate_id'] for c in cases}:
            raise ValueError('Timeline case set differs')
        if any(timeline_index[c['candidate_id']]['nct_id'] != c['origin_record']['nct_id'] for c in cases):
            raise ValueError('Timeline trial identity differs')
        timeline_hash = hashlib.sha256(timeline_path.read_bytes()).hexdigest()
    output.mkdir(exist_ok=False)
    esc = html.escape
    index = {c['candidate_id']: c for c in cases}
    cards = []
    for item in notes['cases']:
        c = index[item['candidate_id']]
        sequence = ''
        if timeline_index:
            observations = timeline_index[c['candidate_id']]['observations']
            sequence = ('<details><summary>Registry observations across snapshots</summary><ul>' + ''.join(
                '<li>' + esc(o['snapshot_date']) + ': ' + esc((o['record'] or {}).get('overall_status') or 'Missing record') +
                ' · ' + esc((o['record'] or {}).get('phase') or 'Unspecified phase') + '</li>' for o in observations) +
                '</ul><p>Observed states do not establish exact first transitions, efficacy or censoring.</p></details>')
        links = ''.join('<li><a href="' + esc(sources[s]['url'], quote=True) + '">' + esc(s) +
            '</a> — ' + esc(sources[s].get('display_label', sources[s]['status'].replace('_', ' '))) + '</li>' for s in item['source_ids'])
        if not links:
            links = '<li>Frozen origin/endpoint registry evidence and retained exact-NCT publication search; no additional eligible primary result established.</li>'
        cards.append('<article><h2>' + esc(c['candidate_id'] + ' · ' + c['drug_anchor']) + '</h2><p class="muted">' +
            esc(c['origin_record']['nct_id'] + ' · ' + c['target_anchor']) + '</p><p class="badge">' +
            esc(item['review_disposition'].replace('_', ' ')) + '</p><p>' + esc(item['finding']) +
            '</p><p><strong>Timing:</strong> ' + esc(item['timing_note']) + '</p><details><summary>Sources and endpoint qualification</summary><p>' +
            esc(item['endpoint_result'].replace('_', ' ') if item['endpoint_result'] else 'Outcome remains unresolved or excluded from the fresh-event cohort.') +
            '</p><ul>' + links + '</ul><p>HTTP retrieval alone does not establish usable content. See retained content-review.json for challenge pages; source IDs with MED bind exact publication metadata/abstracts through Europe PMC.</p></details>' + sequence + '</article>')
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Clinical outcome evidence review</title><style>body{font:17px/1.55 system-ui;max-width:1080px;margin:30px auto;padding:20px;background:#f3f6f9;color:#173047}article{background:white;border:1px solid #cbd7e0;border-radius:12px;margin:20px 0;padding:22px}h2{margin:0;font-size:22px}.muted{color:#506475}.badge{background:#eaf0f6;padding:8px 12px;border-radius:6px;font-size:14px}a{color:#125e9e}summary{cursor:pointer}li{overflow-wrap:anywhere}@media print{body{background:white;font-size:11pt}article{break-inside:avoid}details{display:block}}</style><h1>What the dated evidence supports</h1><p>24 frozen trial representatives · January 2023–January 2025 · AI-assisted development review</p><p><strong>This set is not ready for clinical model training or a predictive-performance claim.</strong> Trial status, result publication, endpoint attainment and program transition are different events. Cases below retain prior-result exclusions, conflicting endpoints, unavailable sources and uncertain timing. They are not independently adjudicated gold.</p><p>The separate registry timeline will show observations from the three newly supplied snapshots once restoration finishes. Original selection and prior artifacts remain unchanged.</p><aside><strong>Linkage test case:</strong> PMID 41051123 describes a retrospective rhinosinusitis study but carries NCT03816891, the vixarelimab trial identifier. Exact ID matching alone must not admit it as an outcome.</aside>' + ''.join(cards) + '</html>'
    page = page.replace('article{background:white;', 'article{overflow-wrap:anywhere;background:white;')
    if timeline_index:
        page = page.replace('The separate registry timeline will show observations from the three newly supplied snapshots once restoration finishes. Original selection and prior artifacts remain unchanged.',
            'Each card includes the verified registry observations. July 2023 uses the actual July 2 dump date. Original selection and prior artifacts remain unchanged.')
    (output / 'Review.html').write_text(page, encoding='utf-8')
    report = {'status': 'authored_development_review_rendered', 'cases': len(cases),
              'review_dispositions': dict(Counter(x['review_disposition'] for x in notes['cases'])),
              'source_receipts': len(sources), 'notes_sha256': hashlib.sha256((root / 'review-notes.json').read_bytes()).hexdigest(),
              'clinical_training_labels': 0, 'independent_program_count': None, 'power_estimate': None,
              'scientific_validation': 'AI_assisted_not_independently_adjudicated',
              'registry_timeline_cases': len(timeline_index), 'timeline_sha256': timeline_hash,
              'source_content_review_sha256': content_hash,
              'timeline_verification_scope': 'local seal and case identity; source-inclusive replay recorded separately' if timeline_index else None}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('root', 'origin', 'output'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--timeline', type=Path)
    args = parser.parse_args()
    print(json.dumps(render(args.root, args.origin, args.output, args.timeline)))
