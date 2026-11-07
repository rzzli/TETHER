"""Freeze contemporary hypothesis identities before biology or system outputs.

Only identifier columns are read. No evidence tables or endpoint records are opened.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unicodedata


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def resolve_cases(proposals, hgnc_rows, target_rows, disease_rows, exposed=()):
    """Fail closed on aliases, ambiguous disease identities and duplicate scopes."""
    approved = {}
    for row in hgnc_rows:
        if row.get('status') == 'Approved':
            approved.setdefault(row['symbol'], []).append(row)
    targets = {}
    for row in target_rows:
        targets.setdefault(row['id'], []).append(row)
    disease_matches = {}
    for row in disease_rows:
        terms = [row['name']] + ((row.get('synonyms') or {}).get('hasExactSynonym') or [])
        for term in terms:
            disease_matches.setdefault(normalized(term), {})[row['id']] = row
    old_targets = {item[0] if isinstance(item, (list, tuple)) else item['symbol'] for item in exposed}
    old_pairs = {(item[0], item[1]) if isinstance(item, (list, tuple)) else (item['symbol'], item['disease_id']) for item in exposed}
    cases, seen = [], set()
    for proposal in proposals:
        symbol = proposal['symbol']
        matches = approved.get(symbol, [])
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous approved HGNC symbol: ' + symbol)
        gene = matches[0]
        ensembl = gene.get('ensembl_gene_id')
        selected = targets.get(ensembl, [])
        if not ensembl or len(selected) != 1 or selected[0]['approvedSymbol'] != symbol:
            raise ValueError('HGNC/OT target identity disagreement: ' + symbol)
        choices = disease_matches.get(normalized(proposal['requested_disease_name']), {})
        requested = proposal.get('disease_id')
        if requested is None:
            if len(choices) != 1:
                raise ValueError('Missing or ambiguous disease: ' + proposal['requested_disease_name'])
            requested = next(iter(choices))
        if requested not in choices:
            raise ValueError('Explicit disease ID does not match exact disease identity')
        if len(choices) > 1 and not proposal.get('identity_choice_reason'):
            raise ValueError('Ambiguous disease selection requires explicit choice rationale')
        action, modality = proposal['intended_action'], proposal['modality']
        if not isinstance(action, str) or not action.strip() or not isinstance(modality, str) or not modality.strip():
            raise ValueError('Action/modality must be explicit')
        if proposal.get('tissue') is not None:
            raise ValueError('This fresh pack requires unspecified tissue')
        scope = (symbol, requested, action, modality, None)
        if scope in seen:
            raise ValueError('Duplicate hypothesis scope')
        if symbol in old_targets or (symbol, requested) in old_pairs:
            raise ValueError('Fresh pack overlaps a prior workflow target or pair')
        seen.add(scope)
        case_id = f'{symbol}-{requested}-{action}-{modality}'.lower()
        cases.append({
            'case_id': case_id, 'symbol': symbol, 'disease_id': requested,
            'intended_action': action, 'modality': modality, 'tissue': None,
            'tissue_reason': 'unspecified_in_development_hypothesis',
            'disease_name': choices[requested]['name'], 'requested_disease_name': proposal['requested_disease_name'],
            'target_id': ensembl, 'hgnc_id': gene['hgnc_id'],
            'scope_sha256': hashlib.sha256(canonical(scope)).hexdigest(),
            'hgnc_gene_group_ids': [v for v in (gene.get('gene_group_id') or '').split('|') if v],
            'resolution_provenance': {
                'hgnc_row': gene['_locator'], 'target_row': selected[0]['_locator'],
                'disease_row': choices[requested]['_locator'],
                'disease_exact_match_alternatives': sorted(choices),
                'identity_choice_reason': proposal.get('identity_choice_reason'),
                'target_row_sha256': hashlib.sha256(canonical({k: v for k, v in selected[0].items() if k != '_locator'})).hexdigest(),
                'hgnc_row_sha256': hashlib.sha256(canonical({k: v for k, v in gene.items() if k != '_locator'})).hexdigest(),
                'disease_row_sha256': hashlib.sha256(canonical({k: v for k, v in choices[requested].items() if k != '_locator'})).hexdigest()
            }
        })
    return cases


def dependency_groups(cases):
    """Conservative declared grouping, not an estimate of statistical independence."""
    parent = list(range(len(cases)))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    links = []
    for i, left in enumerate(cases):
        for j, right in enumerate(cases[:i]):
            reasons = []
            if left['target_id'] == right['target_id']:
                reasons.append('same_target')
            if left['disease_id'] == right['disease_id']:
                reasons.append('same_indication')
            shared = sorted(set(left['hgnc_gene_group_ids']) & set(right['hgnc_gene_group_ids']))
            if shared:
                reasons.append('shared_hgnc_gene_group')
            if reasons:
                parent[find(i)] = find(j)
                links.append({'left': left['case_id'], 'right': right['case_id'], 'reasons': reasons, 'shared_hgnc_group_ids': shared})
    groups = {}
    for i, case in enumerate(cases):
        groups.setdefault(find(i), []).append(case['case_id'])
    return {'basis': 'shared target, exact indication or pinned HGNC gene group; broad groups may over-connect',
            'groups': list(groups.values()), 'links': links,
            'unmeasured_dependence': 'Shared evidence, pathways, publications, disease areas and model knowledge can create additional dependence; ten cases are not ten proven independent units.'}


def checked_identity_sources(inspection_path, raw_root):
    inspection_path, raw_root = Path(inspection_path), Path(raw_root).resolve()
    inspection = json.loads(inspection_path.read_text(encoding='utf-8'))
    if inspection.get('status') != 'inspected':
        raise ValueError('Requires retained successful source inspection')
    sources = []
    for entry in inspection['files']:
        node = entry['source']
        if node['dataset_id'] not in {'ot_target', 'ot_disease', 'hgnc_symbols'}:
            continue
        expected = 'snapshot_2026-10-10' if node['dataset_id'] == 'hgnc_symbols' else '25.09'
        if node['release_id'] != expected:
            raise ValueError('Wrong pinned identity source release')
        path, receipt = (raw_root / node['path']).resolve(), (raw_root / node['receipt_path']).resolve()
        if not path.is_relative_to(raw_root) or not receipt.is_relative_to(raw_root):
            raise ValueError('Identity source or receipt path escape')
        if digest(path) != node['sha256'] or digest(receipt) != node['receipt_sha256']:
            raise ValueError('Pinned identity source/receipt hash mismatch')
        value = json.loads(receipt.read_text(encoding='utf-8'))
        if (value.get('status') != 'completed' or value.get('dataset_id') != node['dataset_id']
                or value.get('release_id') != expected or value.get('sha256') != node['sha256']
                or value.get('bytes') != path.stat().st_size
                or (raw_root / value.get('relative_path', '')).resolve() != path):
            raise ValueError('Identity receipt mismatch')
        sources.append({'dataset_id': node['dataset_id'], 'release_id': expected,
                        'path': str(path), 'sha256': node['sha256'], 'bytes': path.stat().st_size,
                        'receipt_path': str(receipt), 'receipt_sha256': node['receipt_sha256'],
                        'source_url': node.get('source_url'), 'availability': node.get('availability')})
    counts = {kind: sum(s['dataset_id'] == kind for s in sources) for kind in ['ot_target', 'ot_disease', 'hgnc_symbols']}
    if counts != {'ot_target': 10, 'ot_disease': 1, 'hgnc_symbols': 1}:
        raise ValueError('Pinned identity source selection incomplete')
    return sources


def read_identity_rows(sources):
    import pyarrow
    import pyarrow.parquet as pq
    if pyarrow.__version__ != '21.0.0':
        raise ValueError('Identity recipe requires pyarrow==21.0.0')
    genes, targets, diseases = [], [], []
    for source in sources:
        source_key = source['sha256']
        if source['dataset_id'] == 'hgnc_symbols':
            with Path(source['path']).open(encoding='utf-8-sig', newline='') as stream:
                for number, row in enumerate(csv.DictReader(stream, delimiter='\t'), 1):
                    row['_locator'] = {'source_sha256': source_key, 'data_row_1_based': number}
                    genes.append(row)
            continue
        parquet = pq.ParquetFile(source['path'])
        columns = ['id', 'approvedSymbol'] if source['dataset_id'] == 'ot_target' else ['id', 'name', 'synonyms']
        destination = targets if source['dataset_id'] == 'ot_target' else diseases
        for group in range(parquet.num_row_groups):
            for number, row in enumerate(parquet.read_row_group(group, columns=columns).to_pylist()):
                row['_locator'] = {'source_sha256': source_key, 'row_group': group, 'row_in_group': number}
                destination.append(row)
    return genes, targets, diseases


def freeze(proposals_path, inspection_path, raw_root, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    proposals = json.loads(Path(proposals_path).read_text(encoding='utf-8'))
    sources = checked_identity_sources(inspection_path, raw_root)
    from tether_engine.ingest import PILOT
    cases = resolve_cases(proposals['cases'], *read_identity_rows(sources), exposed=PILOT)
    if len(cases) != 10:
        raise ValueError('Fresh pack requires exactly ten hypotheses')
    pack = {'schema_version': 1, 'case_pack_id': 'science-prerequisites-fresh-t6-20261018-v1',
            'frozen_at_utc': datetime.now(timezone.utc).isoformat(), 'role': 'contemporary_development',
            'selected_before_biological_review_and_arm_outputs': True,
            'case_selection': 'Fixed root-prescribed targets/indications/actions/modalities before evidence research; identity resolution only; not random or population-representative.',
            'known_exposure': {'prior_workflow_targets_or_pairs_overlap': False,
                'scope': 'Compared against the original prescribed ten cases only; no claim of all-repository or model-training novelty.',
                'model_training_unseen': None,
                'future_review': 'Root coding/orchestration agents will see evaluator research; future system roles must receive sealed source packets only, not gold answers.'},
            'pre_freeze_amendments': proposals.get('pre_freeze_amendments', []),
            'identity_source_versions': {'open_targets': '25.09', 'hgnc': 'snapshot_2026-10-10'},
            'identity_sources': sources,
            'identity_inspection': {'path': str(Path(inspection_path)), 'sha256': digest(inspection_path)},
            'proposal': {'path': str(Path(proposals_path)), 'sha256': digest(proposals_path)},
            'code_sha256': digest(__file__), 'cases': cases,
            'dependencies': dependency_groups(cases),
            'probabilities': None, 'scientific_validation': 'not_established', 'provider_spend_usd': 0}
    destination = output / 'casepack.json'
    destination.write_text(json.dumps(pack, indent=2, ensure_ascii=False)+'\n', encoding='utf-8', newline='\n')
    seal = {'schema_version': 1, 'path': 'casepack.json', 'sha256': digest(destination),
            'cases': len(cases), 'source_files_rehashed': len(sources), 'role': 'identity_freeze_only'}
    (output / 'freeze-receipt.json').write_text(json.dumps(seal, indent=2)+'\n', encoding='utf-8', newline='\n')
    return seal


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--proposals', type=Path, required=True)
    parser.add_argument('--inspection', type=Path, required=True)
    parser.add_argument('--raw-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(freeze(args.proposals, args.inspection, args.raw_root, args.output)))


if __name__ == '__main__':
    main()
