"""Separate source/native/bootstrap/intervention reconstruction without production imports."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).resolve().parents[4]
METHODS = ROOT/'planning/review-assets/tether-semantic-20261106/methods'


def read(path):
    return json.loads(Path(path).read_bytes())


def rows(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines()]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def load_module(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metric_vector(v):
    result = {}
    for label,g,p,t in [('abstract_label_only',0,1,2),('abstract_rationalized',0,1,3),
                         ('sentence_selection',4,5,6),('sentence_label',4,5,7)]:
        result[label+'_precision'] = v[t]/v[p] if v[p] else 0.
        result[label+'_recall'] = v[t]/v[g] if v[g] else 0.
        result[label+'_f1'] = 2*v[t]/(v[p]+v[g]) if v[p]+v[g] else 0.
    result['strict_correct_per_scheduled'] = v[8]/v[9]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--frame',type=Path,required=True)
    parser.add_argument('--frame-sha256',required=True)
    parser.add_argument('--analysis',type=Path,required=True)
    parser.add_argument('--receipt-sha256',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    checks = 0
    def check(ok,reason):
        nonlocal checks
        checks += 1
        if not ok:
            raise ValueError(reason)
    report = dict(status='FAIL')
    try:
        check(sha(args.frame) == args.frame_sha256,'Experiment anchor')
        check(sha(args.analysis/'RECEIPT.json') == args.receipt_sha256,'Analysis anchor')
        frame = read(args.frame)
        for proof in frame['pins']:
            check(sha(proof['path']) == proof['sha256'] and Path(proof['path']).stat().st_size == proof['bytes'],'Frozen source/input')
        for proof in read(args.analysis/'RECEIPT.json')['files'].values():
            check(sha(proof['path']) == proof['sha256'] and Path(proof['path']).stat().st_size == proof['bytes'],'Analysis file bytes')
        # Previously independent source code rebuilds projections directly from tar
        # members and checks all 1,601 baseline outputs, without production imports.
        source = load_module('sc03_source_reconstruction',METHODS/'source_preflight.py')
        source.OUTPUT = args.output/'raw-source-preflight'
        source.OUTPUT.mkdir()
        source.main()
        check(read(source.OUTPUT/'PREFLIGHT.json')['status'] == 'PASS','Original raw-source reconstruction')
        native_path = METHODS/'independent_native_check.py'
        check(sha(native_path) == '68703fe9713580223e0ed918758ab7f87e9bd00205375aa3a753b9ef1bfd83d8','Independent native code anchor')
        native = load_module('sc03_independent_native',native_path)
        golds = rows(frame['references']['path'])
        new = read(args.analysis/'DISPOSITIONS.json')
        old = read(frame['baseline_dispositions']['path'])
        check([g['id'] for g in golds] == [r['id'] for r in new] == [r['id'] for r in old],'Full ordered 300')
        evaluation = read(args.analysis/'EVALUATION.json')
        independent_vectors = {}
        for name,records in [('baseline',old),('new',new)]:
            predictions = [r['prediction'] if r['check_status']=='accepted' else dict(id=r['id'],evidence={}) for r in records]
            measured = native.counts_and_metrics(golds,predictions)['metrics']
            expected = evaluation['checked_metrics'] if name == 'new' else read(frame['baseline_evaluation']['path'])['checked_metrics']
            check(all(abs(measured[k]-expected[k])<1e-12 for k in measured),'Independent native '+name)
            vectors = {}
            for g,p,r in zip(golds,predictions,records):
                c = native.counts_and_metrics([g],[p])
                a,s = c['abstract'],c['sentence']
                strict = r['producer_status']=='produced' and r['check_status']=='accepted' and set(g['evidence'])==set(p['evidence'])
                if strict:
                    for did, annotations in g['evidence'].items():
                        predicted = p['evidence'][did]
                        cap = max(3,min(len(x['sentences']) for x in annotations))
                        strict = strict and predicted['label']==annotations[0]['label'] and any(
                            set(x['sentences']) <= set(predicted['sentences'][:cap]) for x in annotations)
                vectors[str(g['id'])] = [a.get(k,0) for k in ('gold','predicted','label_correct','rationalized_correct')]
                vectors[str(g['id'])] += [s.get(k,0) for k in ('gold','predicted','selection_correct','label_correct')]
                vectors[str(g['id'])] += [int(strict),1]
            independent_vectors[name] = vectors
            check(vectors == read(args.analysis/'COUNTS.json')[name],'Independent all-case integer statistics '+name)
        # A separate weighted-component implementation reconstructs all 10,000
        # draws, rather than calling the production bootstrap helper.
        grouping = read(frame['split']['path'])['group_by_claim']
        ids = [str(g['id']) for g in golds]
        group_ids = sorted({grouping[cid] for cid in ids})
        members = [[cid for cid in ids if grouping[cid]==group] for group in group_ids]
        def grouped(name):
            return [[sum(independent_vectors[name][cid][j] for cid in group) for j in range(10)] for group in members]
        old_groups,new_groups = grouped('baseline'),grouped('new')
        boot = read(args.analysis/'PAIRED-BOOTSTRAP.json')
        check(boot['seed']==20261106 and boot['replicates']==10000 and boot['components']==247,'Fixed bootstrap frame')
        old_point = metric_vector([sum(v[j] for v in independent_vectors['baseline'].values()) for j in range(10)])
        new_point = metric_vector([sum(v[j] for v in independent_vectors['new'].values()) for j in range(10)])
        for key,entry in boot['metrics'].items():
            check(abs(entry['baseline']-old_point[key])<1e-12 and abs(entry['new']-new_point[key])<1e-12 and
                  abs(entry['difference']-(new_point[key]-old_point[key]))<1e-12,'Paired point estimate '+key)
        rng = random.Random(20261106)
        distribution = {key:[] for key in boot['metrics']}
        for _ in range(10000):
            frequencies = Counter(rng.randrange(len(group_ids)) for _ in group_ids)
            def sampled(groups):
                return metric_vector([sum(groups[i][j]*weight for i,weight in frequencies.items()) for j in range(10)])
            a,b = sampled(old_groups),sampled(new_groups)
            for key in distribution:
                distribution[key].append(b[key]-a[key])
        for key,values in distribution.items():
            values.sort()
            for label,p in [('lower',.025),('upper',.975)]:
                index = p*(len(values)-1)
                lo,hi = math.floor(index),math.ceil(index)
                value = values[lo]+(values[hi]-values[lo])*(index-lo)
                check(abs(value-boot['metrics'][key][label])<1e-12,'Bootstrap interval '+key+'/'+label)
        prepared = read(frame['prepared']['path'])
        primary_root = Path(read(frame['conditions']['primary']['path'])['qualification_output'])
        diagnostic_summaries = {}
        for condition in frame['condition_order'][1:]:
            condition_root = Path(read(frame['conditions'][condition]['path'])['qualification_output'])
            expected = read(args.analysis/(condition+'-diagnostics.json'))
            expected_rows = {(r['claim_id'],r['doc_id']):r for r in expected['rows']}
            check(len(expected_rows)==len(expected['rows'])==1500,'Unique diagnostic rows')
            both = applicable = changed = synthetic = 0
            delta = []
            for lineage in rows(prepared['conditions'][condition]['lineage']['path']):
                cid = lineage['id']
                for doc in lineage['documents']:
                    did = doc['doc_id']
                    a,b = read(primary_root/f'pairs/{cid}-{did}.json'),read(condition_root/f'pairs/{cid}-{did}.json')
                    row = expected_rows[(cid,did)]
                    observed = a['status']==b['status']=='completed'
                    check(row['both_observed']==observed and row['primary_status']==a['status'] and row['condition_status']==b['status'],
                          'Diagnostic disposition')
                    check(row['reference_mask_applicable'] is doc['annotated_rationale_applicable'] and
                          row['input_changed']==(doc['input_document_sha256']!=doc['source_document_sha256']),
                          'Diagnostic applicability/source change')
                    if not observed:
                        continue
                    both += 1
                    pa,pb = a['prediction'],b['prediction']
                    labels = ['CONTRADICT','NEI','SUPPORT']
                    probability_delta = pb['label_probs'][labels.index(pa['predicted_label'])]-pa['label_probs'][labels.index(pa['predicted_label'])]
                    selected = [doc['sentences'][i] for i in pb['predicted_rationale']]
                    genuine = sorted(s['original_index'] for s in selected if s['original_index'] is not None)
                    fabricated = [s for s in selected if s['original_index'] is None]
                    check(row['condition_source_rationale_indices']==genuine and row['synthetic_selections']==fabricated,
                          'Independent diagnostic source mapping')
                    old_indices = set(pa['predicted_rationale'])
                    new_indices = set(genuine)
                    jaccard = len(old_indices & new_indices)/len(old_indices | new_indices) if old_indices | new_indices else None
                    check(row['primary_rationale_indices']==sorted(old_indices) and row['rationale_jaccard']==jaccard,
                          'Rationale overlap')
                    check(abs(row['primary_class_probability_change']-probability_delta)<1e-12 and
                          row['label_changed']==(pa['predicted_label']!=pb['predicted_label']),'Diagnostic scores')
                    if doc['annotated_rationale_applicable'] is not False:
                        applicable += 1
                        changed += pa['predicted_label']!=pb['predicted_label']
                        synthetic += len(fabricated)
                        delta.append(probability_delta)
            check(expected['scheduled_pairs']==1500 and expected['both_observed_pairs']==both and
                  expected['applicable_observed_pairs']==applicable and expected['changed_labels']==changed and
                  expected['synthetic_sentences_selected']==synthetic,'Diagnostic all-pair aggregate')
            mean = sum(delta)/len(delta) if delta else None
            check(mean == expected['mean_primary_class_probability_change'],'Diagnostic aggregate score')
            diagnostic_summaries[condition] = dict(both_observed=both,applicable_observed=applicable,changed_labels=changed,
                                                  synthetic_sentences_selected=synthetic)
        report.update(status='PASS',native_claims=300,components=247,bootstrap_replicates=10000,
            diagnostic_summaries=diagnostic_summaries,production_modules_imported=False,
            scope='Independent code reconstruction, not independent scientific annotation or a new holdout.',
            frame_sha256=args.frame_sha256,analysis_receipt_sha256=args.receipt_sha256,
            independent_native_source_sha256=sha(native_path))
    except BaseException as error:
        report.update(error_type=type(error).__name__,error=str(error))
    report.update(checks=checks,reviewer_sha256=sha(__file__))
    with (args.output/'INDEPENDENT-REVIEW.json').open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(report,stream,indent=2,sort_keys=True)
        stream.write('\n')
    print(json.dumps(report))
    return 0 if report['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
