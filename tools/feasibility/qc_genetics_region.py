"""Regional technical QC and allele-oriented external-reference LD, not causal inference."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import time


def effect_orientation(ref, alt, effect, other):
    if any(len(a) != 1 or a not in 'ACGT' for a in (ref,alt,effect,other)):
        return None
    if ref == alt or effect == other:
        return None
    if {ref,alt} in ({'A','T'}, {'C','G'}):
        return None
    if (effect,other)==(alt,ref):
        return 1
    if (effect,other)==(ref,alt):
        return -1
    return None


def valid_stats(beta, se, p):
    try:
        b,s,v = map(float,(beta,se,p))
        return math.isfinite(b) and math.isfinite(s) and s>0 and math.isfinite(v) and 0<=v<=1
    except (ValueError,TypeError):
        return False


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--numpy-path',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(args.numpy_path))
    import numpy as np
    root=args.root
    out=root/'qc'
    out.mkdir(exist_ok=False)
    protocol=json.loads((root/'protocol.json').read_text())
    receipts=json.loads((root/'regional-receipts.json').read_text())
    if any(r['status']!='retrieved' for r in receipts) or len(receipts)!=3:
        raise ValueError('Incomplete regional acquisition')
    for r in receipts:
        if hashlib.sha256((root/'regional_originals'/r['output']).read_bytes()).hexdigest()!=r['sha256']:
            raise ValueError('Regional source hash mismatch')
    started=time.monotonic()
    report={'status':'running','numpy_version':np.__version__,'counts':{},'exclusions':[],
        'region':protocol['region'],'gene_id':protocol['gene_id'],
        'clinical_or_causal_inference_performed':False}
    def save(): (out/'report.json').write_bytes((json.dumps(report,indent=2)+'\n').encode())
    save()
    def records(name):
        fields=(root/(name+'-header.txt')).read_text().strip().split('\t')
        with gzip.open(root/'regional_originals'/(name+'.region.tsv.gz'),'rt',encoding='utf-8') as stream:
            for row in csv.DictReader(stream,fieldnames=fields,delimiter='\t'):
                if None in row or None in row.values(): raise ValueError('Row/schema mismatch')
                yield row
    qtl={};qtl_conflicts=set();duplicates=0;gene_rows=0
    for row in records('eqtl'):
        if row['gene_id']!=protocol['gene_id'] or row['molecular_trait_id']!=protocol['gene_id']:
            continue
        gene_rows+=1
        key=(row['chromosome'],int(row['position']),row['ref'],row['alt'])
        if key in qtl:
            if {k:v for k,v in row.items() if k!='rsid'}!={k:v for k,v in qtl[key].items() if k!='rsid'}:
                qtl_conflicts.add(key)
            else: duplicates+=1
        qtl[key]=row
    gwas={};gwas_conflicts=set();gwas_duplicates=0
    for row in records('gwas'):
        key=(row['chromosome'],int(row['base_pair_location']),tuple(sorted((row['effect_allele'],row['other_allele']))))
        if key in gwas:
            if row!=gwas[key]:gwas_conflicts.add(key)
            else:gwas_duplicates+=1
        gwas[key]=row
    if not qtl or not gwas:raise ValueError('No gene-specific QTL or regional GWAS records')
    with (root/'sample-panel.txt').open() as f:
        panel=list(csv.DictReader(f,delimiter='\t'))
    eur={x['sample']:x['pop'] for x in panel if x['super_pop']=='EUR'}
    wanted={};flips=0
    for key,q in qtl.items():
        gkey=(key[0],key[1],tuple(sorted(key[2:])))
        reason=None
        if key in qtl_conflicts:reason='conflicting_qtl_duplicate'
        elif gkey in gwas_conflicts:reason='conflicting_gwas_duplicate'
        elif gkey not in gwas:reason='no_allele_matched_gwas'
        else:
            g=gwas[gkey];sign=effect_orientation(*key[2:],g['effect_allele'],g['other_allele'])
            if sign is None:reason='palindromic_or_non_biallelic_snp_or_allele_mismatch'
            elif not valid_stats(q['beta'],q['se'],q['pvalue']) or not valid_stats(g['beta'],g['standard_error'],g['p_value']):reason='invalid_or_missing_statistics'
            else:wanted[key]=(q,g,sign)
        if reason:report['exclusions'].append({'variant':list(key),'reason':reason})
    genotypes={};ld_conflicts=set();sample_ids=[];sample_indices=[];vcf_count=0
    with gzip.open(root/'regional_originals/ld.region.tsv.gz','rt') as f:
        for line in f:
            if line.startswith('##'):continue
            fields=line.rstrip('\n').split('\t')
            if line.startswith('#CHROM'):
                sample_ids=[s for s in fields[9:] if s in eur]
                sample_indices=[i for i,s in enumerate(fields[9:]) if s in eur]
                report['vcf_samples_total']=len(fields)-9
                continue
            if not sample_ids:raise ValueError('No EUR samples/header')
            vcf_count+=1
            key=(fields[0].removeprefix('chr'),int(fields[1]),fields[3],fields[4])
            if key not in wanted:continue
            if key in genotypes:ld_conflicts.add(key)
            fmt=fields[8].split(':')
            if 'GT' not in fmt:continue
            gi=fmt.index('GT');values=[]
            for index in sample_indices:
                gt=fields[9+index].split(':')[gi].replace('|','/').split('/')
                values.append(sum(map(int,gt)) if len(gt)==2 and all(a in ('0','1') for a in gt) else -1)
            genotypes[key]=values
    if set(sample_ids)!=set(eur):raise ValueError('EUR panel membership incomplete')
    selected=[];dosages=[]
    for key,(q,g,sign) in sorted(wanted.items()):
        reason=None
        if key in ld_conflicts:reason='duplicate_ld_key'
        elif key not in genotypes:reason='no_exact_ref_alt_ld_record'
        elif -1 in genotypes[key]:reason='missing_or_non_diploid_ld_genotype'
        else:
            frequency=sum(genotypes[key])/(2*len(sample_ids));maf=min(frequency,1-frequency)
            if maf<0.01:reason='ld_maf_below_0.01_including_monomorphic'
            else:
                selected.append({'chromosome':key[0],'position':key[1],'ref':key[2],'alt':key[3],
                    'qtl_beta_alt':float(q['beta']),'qtl_se':float(q['se']),'qtl_p':float(q['pvalue']),
                    'qtl_reported_an':int(q['an']),'qtl_maf':float(q['maf']),
                    'gwas_beta_alt':float(g['beta'])*sign,'gwas_se':float(g['standard_error']),
                    'gwas_p':float(g['p_value']),'gwas_effect_allele_original':g['effect_allele'],
                    'gwas_effect_allele_frequency_original':g['effect_allele_frequency'],
                    'gwas_variant_sample_size':None,'gwas_orientation_sign':sign,
                    'ld_alt_frequency':frequency,'ld_samples':len(sample_ids)})
                dosages.append(genotypes[key]);flips+=sign==-1
        if reason:report['exclusions'].append({'variant':list(key),'reason':reason})
    if len(selected)<2:raise ValueError('Insufficient shared QC-passing variants')
    x=np.asarray(dosages,dtype=np.float64)
    centered=x-x.mean(axis=1,keepdims=True)
    norm=np.sqrt(np.sum(centered**2,axis=1,keepdims=True))
    standardized=centered/norm
    ld=standardized@standardized.T
    if not np.isfinite(ld).all() or not np.allclose(ld,ld.T,atol=1e-12) or not np.allclose(np.diag(ld),1,atol=1e-12):
        raise ValueError('LD integrity check failed')
    np.save(out/'ld.alt-oriented.npy',ld,allow_pickle=False)
    np.save(out/'dosages.alt-oriented.npy',x.astype(np.int8),allow_pickle=False)
    (out/'variant-order.json').write_bytes(json.dumps(selected,indent=2).encode())
    (out/'sample-order.json').write_bytes(json.dumps([{'sample':s,'population':eur[s]} for s in sample_ids],indent=2).encode())
    report.update(status='completed',counts={'qtl_gene_rows':gene_rows,'qtl_unique_variants':len(qtl),
        'qtl_rsid_duplicate_rows':duplicates,'qtl_conflicting_keys':len(qtl_conflicts),
        'gwas_unique_variant_allele_keys':len(gwas),'gwas_duplicate_rows':gwas_duplicates,
        'gwas_conflicting_keys':len(gwas_conflicts),'ld_regional_records':vcf_count,
        'shared_after_qc':len(selected),'gwas_beta_flips':flips,'ld_samples':len(sample_ids)},
        exclusion_counts=dict(Counter(x['reason'] for x in report['exclusions'])),
        ld_checks={'finite':True,'symmetric':True,'unit_diagonal':True,
            'construction':'Gram matrix of centered, unit-norm ALT dosage vectors; expected singular if variants >= samples. No inversion/regularization.'},
        limitations=['External European LD is a proxy, not BLUEPRINT or RA cohort LD',
            'Cohort overlap remains unknown','GWAS per-variant N and effect allele frequencies are not imputed',
            'Complete interval means indexed source records for the interval, not every genomic variant or full cis window',
            'QTL measures monocyte transcript abundance, not IL6R protein concentration or drug blockade',
            'Current annotations/2023+ processed releases are not admitted to January 2023 historical inputs'],
        elapsed_seconds=time.monotonic()-started)
    save()
    print(json.dumps({k:v for k,v in report.items() if k!='exclusions'}))


if __name__=='__main__':main()
