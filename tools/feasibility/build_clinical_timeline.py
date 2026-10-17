"""Build evaluator-only observed registry timelines from dated, sealed extracts."""
from __future__ import annotations
import argparse
from collections import Counter
from datetime import date
import hashlib
import html
import json
from pathlib import Path

from tools.feasibility.compare_clinical_snapshots import normalized


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def timelines(selected, snapshots, endpoint):
    date.fromisoformat(endpoint)
    ids = [c['origin_record']['nct_id'] for c in selected]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate frozen selection')
    dates = [s['snapshot_date'] for s in snapshots]
    if not dates or dates != sorted(set(dates)):
        raise ValueError('Distinct chronological snapshot dates required')
    indexed = []
    for s in snapshots:
        date.fromisoformat(s['snapshot_date'])
        if s['snapshot_date'] > endpoint:
            raise ValueError('Post-endpoint snapshot cannot enter frozen timeline')
        index = {}
        for r in s['records']:
            nct = r['nct_id']
            if nct not in ids or nct in index:
                raise ValueError('Duplicate or unselected trial')
            for field in ('study_first_posted_date', 'last_update_posted_date', 'results_first_posted_date'):
                if r.get(field):
                    date.fromisoformat(r[field])
                    if r[field] > s['snapshot_date']:
                        raise ValueError('Later publication date in dated extract')
            index[nct] = r
        indexed.append(index)
    result = []
    for case in selected:
        nct = case['origin_record']['nct_id']
        observations, differences = [], []
        previous = None
        for snapshot, index in zip(snapshots, indexed):
            record = index.get(nct)
            observation = {'snapshot_date': snapshot['snapshot_date'], 'record': record,
                           'availability_basis': snapshot['availability_basis'],
                           'coverage': 'record_present' if record else 'missing_record_not_absence_or_failure'}
            observations.append(observation)
            if previous and previous['record'] and record:
                old = previous['record']
                for field in ('overall_status', 'phase'):
                    a, b = normalized(old.get(field)), normalized(record.get(field))
                    if field == 'phase':
                        a, b = a.replace('_', ''), b.replace('_', '')
                    if a != b:
                        differences.append({'field': field, 'observed_from': old.get(field),
                            'observed_to': record.get(field), 'earlier_observation': previous['snapshot_date'],
                            'later_observation': snapshot['snapshot_date'],
                            'interpretation': 'different_observed_states_not_exact_first_public_transition',
                            'monotonicity_assumed': False, 'clinical_event_date': None})
            # Missing observations break adjacency; do not manufacture a narrower bound.
            previous = observation
        result.append({'candidate_id': case['candidate_id'], 'nct_id': nct,
            'target_anchor': case['target_anchor'], 'drug_anchor': case['drug_anchor'],
            'observations': observations, 'observed_differences': differences,
            'administrative_endpoint': endpoint, 'clinical_outcome': None, 'censoring_date': None,
            'scientific_validation': 'not_established', 'role': 'evaluation_only'})
    return result


def build(manifest, output):
    # Complete input/proof checks before reserving output; no database calls here.
    selected_path = Path(manifest['selected_path'])
    if sha(selected_path) != manifest['selected_sha256']:
        raise ValueError('Frozen selection changed')
    snapshots = []
    inputs = []
    for item in manifest['snapshots']:
        path = Path(item['path'])
        if sha(path) != item['sha256']:
            raise ValueError('Snapshot extract changed')
        proof = Path(item['evidence_manifest'])
        if sha(proof) != item['evidence_manifest_sha256']:
            raise ValueError('Snapshot evidence anchor changed')
        entry = next((x for x in load(proof)['files'] if
            (proof.parent / x['path']).resolve() == path.resolve()), None)
        if not entry or entry['sha256'] != item['sha256']:
            raise ValueError('Extract missing from sealed evidence')
        records = load(path)
        if item.get('format') == 'selected_cases':
            records = [c['origin_record'] for c in records]
        snapshots.append({'snapshot_date': item['snapshot_date'], 'records': records,
                          'availability_basis': item['availability_basis']})
        inputs.append(item)
    rows = timelines(load(selected_path), snapshots, manifest['endpoint'])
    output.mkdir(exist_ok=False)
    def write(name, value):
        (output / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    write('input-manifest.json', manifest)
    write('timeline.json', rows)
    summary = {'status': 'observed_registry_timeline_completed', 'trials': len(rows),
               'snapshot_dates': [s['snapshot_date'] for s in snapshots],
               'differences_by_field': dict(Counter(d['field'] for r in rows for d in r['observed_differences'])),
               'missing_observations': sum(o['record'] is None for r in rows for o in r['observations']),
               'clinical_labels_assigned': 0, 'censoring_dates_assigned': 0}
    write('summary.json', summary)
    cards = []
    esc = html.escape
    for r in rows:
        states = ''.join('<tr><td>' + esc(o['snapshot_date']) + '</td><td>' +
            esc(((o['record'] or {}).get('overall_status') or 'Missing').replace('_', ' ')) + '</td><td>' +
            esc((o['record'] or {}).get('phase') or 'Unspecified') + '</td></tr>' for o in r['observations'])
        cards.append('<article><h2>' + esc(r['candidate_id'] + ' · ' + r['drug_anchor']) + '</h2><p>' +
            esc(r['nct_id']) + '</p><table><thead><tr><th>Snapshot</th><th>Registry status</th><th>Phase field</th></tr></thead><tbody>' +
            states + '</tbody></table><details><summary>Original fields and observed differences</summary><pre>' +
            esc(json.dumps(r, indent=2, ensure_ascii=False)) + '</pre></details></article>')
    page = '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Clinical registry timeline</title><style>body{font:17px/1.5 system-ui;max-width:1050px;margin:30px auto;padding:20px;background:#f5f7fa;color:#152c40}article{overflow-wrap:anywhere;background:white;padding:20px;margin:20px 0;border:1px solid #ced8e1;border-radius:10px}table{border-collapse:collapse;width:100%;table-layout:fixed}td,th{text-align:left;padding:8px;border-bottom:1px solid #ddd}pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}summary{cursor:pointer}@media(max-width:600px){body{font-size:15px;padding:12px}article{padding:14px}td,th{font-size:13px;padding:5px}}</style><h1>Observed trial states across five snapshots</h1><p>Frozen January 2023–January 2025 development cohort. July 2023 uses the actual July 2 dump date. Snapshot dates are not verified first-public availability timestamps. Differences do not establish exact transition dates, efficacy, failure or censoring.</p>' + ''.join(cards) + '</html>'
    (output / 'Review.html').write_text(page, encoding='utf-8')
    write('provenance.json', {'code_sha256': sha(Path(__file__)), 'inputs': inputs,
                             'scientific_validation': 'not_established', 'role': 'evaluation_only'})
    write('evidence-manifest.json', {'files': [{'path': p.name, 'sha256': sha(p), 'bytes': p.stat().st_size}
        for p in sorted(output.iterdir()) if p.is_file()]})
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(load(args.manifest), args.output)))
