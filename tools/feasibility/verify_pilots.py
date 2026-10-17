"""Read-only replay and independent checks for the bounded feasibility artifacts."""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
from pathlib import Path
import sys

from tools.feasibility.audit_clinical_origin import select


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(clinical, genetics, numpy_path):
    sys.path.insert(0, str(numpy_path))
    import numpy as np
    selected, excluded = select(load(clinical/'origin-records.json'), load(clinical/'protocol.json'))
    require(selected == load(clinical/'selected.json'), 'Clinical selection replay differs')
    require(excluded == load(clinical/'excluded.json'), 'Clinical exclusions replay differs')
    extraction = load(clinical/'extraction-report.json')
    for filename, field in [('origin-records.json', 'source_sha256'), ('protocol.json', 'protocol_sha256'),
                            ('executed-extraction-script.py', 'code_sha256')]:
        require(sha(clinical/filename) == extraction[field], 'Extraction fingerprint mismatch')
    review = load(clinical/'mapping-review.json')
    ids = {c['origin_record']['nct_id'] for c in selected}
    require(len(ids) == 24 and ids == {r['nct_id'] for r in review}, 'Clinical review identity mismatch')
    for row in selected:
        require(all(row[k] is None for k in ('therapeutic_success', 'clinical_failure', 'event_date',
                    'event_publication_date', 'censoring_date')), 'Premature clinical label')
    for receipt in load(clinical/'current-record-receipts.json'):
        path = clinical/'current_records'/(receipt['nct_id']+'.json')
        require(sha(path) == receipt['sha256'] and path.stat().st_size == receipt['bytes'], 'Current record mismatch')
    for receipt in load(genetics/'metadata-receipts.json'):
        require(sha(genetics/receipt['file']) == receipt['sha256'], 'Metadata hash mismatch')
    regional = load(genetics/'regional-receipts.json')
    counts = {}
    for receipt in regional:
        path = genetics/'regional_originals'/receipt['output']
        require(sha(path) == receipt['sha256'], 'Regional hash mismatch')
        require(sha(genetics/'regional_originals'/(receipt['source']+'.tbi')) == receipt['index_sha256'], 'Index hash mismatch')
        count = 0
        with gzip.open(path, 'rt', encoding='utf-8') as stream:
            for line in stream:
                if line.startswith('#'):
                    continue
                fields = line.split('\t')
                require(fields[0].removeprefix('chr') == '1' if receipt['source'] != 'eqtl' else fields[1] == '1', 'Wrong chromosome')
                pos = int(fields[2] if receipt['source'] == 'eqtl' else fields[1])
                require(153900000 <= pos <= 154900000, 'Out-of-region source row')
                count += 1
        require(count == receipt['rows'], 'Regional row count differs')
        counts[receipt['source']] = count
    # Provider checksum strings must actually occur in the retained provider manifests.
    md5s = [('regional_originals/gwas.tbi','7c9f54be487f629a4ea54ab2fe5f1511','gwas-md5.txt'),
            ('regional_originals/ld.tbi','fddc39a4f2357ad0211d6aace27210ae','ld-manifest.txt')]
    for filename, digest, manifest in md5s:
        require(digest in (genetics/manifest).read_text(), 'Provider checksum absent')
        require(hashlib.md5((genetics/filename).read_bytes()).hexdigest() == digest, 'Provider MD5 mismatch')
    qc = genetics/'qc'
    report = load(qc/'report.json')
    variants, samples = load(qc/'variant-order.json'), load(qc/'sample-order.json')
    dosage = np.load(qc/'dosages.alt-oriented.npy', allow_pickle=False)
    ld = np.load(qc/'ld.alt-oriented.npy', allow_pickle=False)
    require(dosage.shape == (1690,503) and ld.shape == (1690,1690), 'Array shape mismatch')
    require(len(variants) == 1690 and len({s['sample'] for s in samples}) == 503, 'Array order mismatch')
    require(np.isfinite(ld).all() and np.allclose(ld,ld.T) and np.allclose(np.diag(ld),1), 'Invalid LD matrix')
    require(np.isin(dosage, [0,1,2]).all(), 'Invalid diploid dosage')
    indices = np.linspace(0, len(variants)-1, 40, dtype=int)
    independent = np.corrcoef(dosage[indices])
    require(np.allclose(independent, ld[np.ix_(indices,indices)], atol=1e-12), 'Independent LD recomputation differs')
    require(sum(report['exclusion_counts'].values())+len(variants) == report['counts']['qtl_unique_variants'], 'QC accounting mismatch')
    require(np.allclose(dosage.mean(axis=1)/2, [v['ld_alt_frequency'] for v in variants]), 'Allele frequency mismatch')
    with (genetics/'sample-panel.txt').open() as stream:
        expected = {r['sample'] for r in csv.DictReader(stream,delimiter='\t') if r['super_pop']=='EUR'}
    require(expected == {s['sample'] for s in samples}, 'European panel mismatch')
    metadata_exception = load(genetics/'gwas-metadata-recheck.json')
    require(metadata_exception['same_bytes'] and metadata_exception['observed_md5'] ==
            hashlib.md5((genetics/'gwas-metadata.yaml').read_bytes()).hexdigest(), 'Unverified metadata exception')
    return {'status':'passed_with_source_exceptions', 'clinical_selection_replay':'identical', 'clinical_cases':len(selected),
            'clinical_current_record_hashes':24, 'clinical_labels_assigned':0, 'regional_rows_verified':counts,
            'provider_index_md5_checks_passed':2, 'provider_metadata_md5':'mismatch_unresolved_identical_redownload',
            'shared_variants':len(variants), 'ld_samples':len(samples),
            'independent_correlation_submatrix_variants':len(indices),
            'gwas_missing_effect_allele_frequencies':sum(v['gwas_effect_allele_frequency_original']=='NA' for v in variants),
            'qtl_reported_an_range':[min(v['qtl_reported_an'] for v in variants),max(v['qtl_reported_an'] for v in variants)],
            'source_discrepancy':'LD README states N=5248; observed VCF header has 2548. All 503 requested EUR samples present.',
            'scientific_validation':'not_established'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clinical',type=Path,required=True)
    parser.add_argument('--genetics',type=Path,required=True)
    parser.add_argument('--numpy-path',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    result = verify(args.clinical,args.genetics,args.numpy_path)
    with args.output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(result))
