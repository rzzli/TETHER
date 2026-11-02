"""Bounded catalog/status inventory. Stat named originals; do not decode outcomes."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
RAW = Path('E:/projects_data/drug_target_agents_data')


def main():
    raw = (ROOT / 'data/catalog/sources.json').read_bytes()
    catalog = json.loads(raw)
    ds = {d['dataset_id']: d for d in catalog['datasets']}
    from asof.maintenance import validate_catalog
    validate_catalog(catalog)
    families = {}
    for name in sorted({d['family'] for d in ds.values()}):
        rows = [d for d in ds.values() if d['family'] == name]
        families[name] = {'products': len(rows), 'collection': dict(Counter(d['collection_status'] for d in rows)),
                          'dataset_ids': [d['dataset_id'] for d in rows]}
    refs = {}
    skipped = []
    tainted_edges = []
    paths = []
    contradictions = []
    for d in ds.values():
        for p in d['dependencies']:
            if 'agent_evidence' in d['roles'] and 'evaluation_only' in ds[p]['roles']:
                tainted_edges.append({'child': d['dataset_id'], 'parent': p})
        for e in d['verification']['evidence']:
            path = e.get('workspace_path')
            if not path:
                continue
            if any(part in path.lower() for part in ('expert', 'response', 'normalized-outcome', 'adjudication')):
                skipped.append(path)
                continue
            f = ROOT / path
            item = {'path': path, 'exists': f.is_file(), 'pinned_sha256': e.get('sha256')}
            if f.is_file():
                item['bytes'] = f.stat().st_size
                if e.get('sha256') and item['bytes'] <= 16 * 1024 * 1024:
                    item['hash_matches'] = hashlib.sha256(f.read_bytes()).hexdigest() == e['sha256']
            refs[path] = item
        acq = d.get('acquisition_snapshot') or {}
        for rel in acq.get('relative_paths', []):
            f = RAW / rel.replace('\\', '/')
            if not f.resolve().is_relative_to(RAW.resolve()):
                raise ValueError('Unsafe catalog original path')
            paths.append({'dataset_id': d['dataset_id'], 'relative_path': rel,
                          'exists': f.is_file(), 'bytes': f.stat().st_size if f.is_file() else None})
        if d['collection_status'] == 'collected' and 'No acquired artifact in this scaffold.' in d['temporal'].get('unknowns', []):
            contradictions.append(d['dataset_id'])
    report = {'schema_version': 1, 'method': 'tether.bounded_data_catalog_review.v1',
              'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'role': 'evaluation_only', 'agent_visible': False,
              'status': 'PASS_STRUCTURAL_INVENTORY_WITH_REVIEW_FINDINGS',
              'catalog_sha256': hashlib.sha256(raw).hexdigest(),
              'providers': len(catalog['providers']), 'datasets': len(ds),
              'collection_status': dict(Counter(d['collection_status'] for d in ds.values())),
              'parse_status': dict(Counter(d['parse_status'] for d in ds.values())),
              'validation_status': dict(Counter(d['validation_status'] for d in ds.values())),
              'temporal_classification': dict(Counter(d['temporal']['classification'] for d in ds.values())),
              'families': families, 'evaluator_dependency_conflicts': tainted_edges,
              'collected_with_stale_no_artifact_note': contradictions,
              'verification_references': list(refs.values()), 'excluded_protected_references': skipped,
              'named_original_stat_checks': paths,
              'original_scope': 'Existence/size only for catalog-named paths; no whole-drive scan, no original hash refresh or content decoding.',
              'named_paths': len(paths), 'named_paths_present': sum(p['exists'] for p in paths),
              'new_downloads': 0, 'models_called': 0, 'scientific_validation': 'not_performed'}
    (HERE / 'CATALOG-AND-INVENTORY.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('providers','datasets','collection_status','parse_status','validation_status','temporal_classification','evaluator_dependency_conflicts','collected_with_stale_no_artifact_note','named_paths','named_paths_present')}))
    print(json.dumps({'missing_metadata_refs': [r['path'] for r in refs.values() if not r['exists']],
                      'mismatched_metadata_refs': [r['path'] for r in refs.values() if r.get('hash_matches') is False]}))


if __name__ == '__main__':
    main()
