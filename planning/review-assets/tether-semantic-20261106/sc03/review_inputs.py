"""Independent stdlib reconstruction of all SC03 request/lineage products."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def load(path):
    return json.loads(Path(path).read_bytes())


def rows(path):
    return [json.loads(line) for line in Path(path).read_bytes().splitlines()]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    checks = 0
    def check(ok, message):
        nonlocal checks
        checks += 1
        if not ok:
            raise ValueError(message)
    result = dict(status='FAIL')
    try:
        check(file_hash(args.manifest) == args.sha256, 'Manifest anchor')
        manifest = load(args.manifest)
        for proof in manifest['source_parents'] + manifest['source_pins'] + [manifest['protocol'], manifest['retrieval']]:
            check(file_hash(proof['path']) == proof['sha256'] and Path(proof['path']).stat().st_size == proof['bytes'], 'Parent/source changed')
        prepared = ROOT/'data/benchmark/scifact/preparation-20261105-attempt03'
        baseline = ROOT/'data/benchmark/scifact/native-20261105T234805Z-attempt01'
        source_manifest = load(prepared/'manifest.json')
        def product(key):
            proof = source_manifest['products'][key]
            path = prepared/proof['path']
            check(file_hash(path) == proof['sha256'], 'Original product anchor')
            return rows(path)
        corpus = {d['doc_id']: d for d in product('corpus')}
        queries = {q['id']: q['claim'] for q in product('queries_dev')}
        references = {r['id']:r for r in product('references_dev')}
        original_candidates = load(baseline/'check-inputs/candidates.json')
        check(file_hash(baseline/'check-inputs/candidates.json') ==
              load(baseline/'RECEIPT.json')['outputs']['check-inputs/candidates.json'], 'Retained retrieval binding')
        retrieval = {int(c['cell_id']):c['result']['retrieved'] for c in original_candidates}
        check(rows(manifest['retrieval']['path']) == [dict(id=i,retrieved=retrieval[i]) for i in manifest['schedule']],
              'Ranks and scores equal original retrieval')
        counts = {}
        for condition, spec in manifest['conditions'].items():
            for field in ('requests', 'lineage'):
                proof = spec[field]
                check(file_hash(proof['path']) == proof['sha256'] and Path(proof['path']).stat().st_size == proof['bytes'], 'Output hash')
            actual, lineages = rows(spec['requests']['path']), rows(spec['lineage']['path'])
            check([q['id'] for q in actual] == manifest['schedule'] == [q['id'] for q in lineages], 'Full ordered schedule')
            annotated = empty = synthetic = pairs = 0
            for query, lineage in zip(actual, lineages):
                cid = query['id']
                originals = [corpus[item['doc_id']] for item in retrieval[cid]]
                check(set(query) == {'id','claim','documents'} and query['claim'] == queries[cid], 'Worker query projection')
                check(len(query['documents']) == len(lineage['documents']) == 5, 'Five retrieved pairs')
                primary = dict(id=cid, claim=queries[cid], documents=originals)
                check(lineage['condition'] == condition and lineage['primary_request_sha256'] == fingerprint(primary)
                      and lineage['request_sha256'] == fingerprint(query), 'Request lineage fingerprint')
                for doc, origin, source in zip(query['documents'], lineage['documents'], originals):
                    pairs += 1
                    did = source['doc_id']
                    check(doc['doc_id'] == origin['doc_id'] == did and doc['title'] == source['title'], 'Exact document/title')
                    check(origin['source_document_sha256'] == fingerprint(source) and
                          origin['input_document_sha256'] == fingerprint(doc), 'Distinct source/input hashes')
                    mask = {i for r in references[cid]['evidence'].get(str(did), []) for i in r['sentences']}
                    relevant = bool(mask) if condition in ('rationale_only','evidence_removal') else None
                    annotated += relevant is True
                    original_indices = list(range(len(source['abstract'])))
                    if relevant:
                        original_indices = [i for i in original_indices if
                            (i in mask if condition == 'rationale_only' else i not in mask)]
                    expected = [source['abstract'][i] for i in original_indices]
                    mapped = list(original_indices)
                    if condition == 'irrelevant_context':
                        expected.append('In a fictional observatory, the blue telescope was stored beside an unused wooden cabinet.')
                        mapped.append(None)
                    elif condition == 'constructed_conflict':
                        expected.append('For this constructed counterfactual, the following statement is false: ' + queries[cid])
                        mapped.append(None)
                    check(doc['abstract'] == expected, 'Exact independent intervention reconstruction')
                    check(origin['annotated_rationale_applicable'] is relevant, 'Applicability')
                    check(len(origin['sentences']) == len(expected), 'Complete sentence lineage')
                    for index, (text, original_index, binding) in enumerate(zip(expected, mapped, origin['sentences'])):
                        is_synthetic = original_index is None
                        synthetic += is_synthetic
                        check(binding == dict(input_index=index, original_index=original_index,
                            origin='synthetic_' + condition if is_synthetic else 'source',
                            text_sha256=hashlib.sha256(text.encode()).hexdigest()), 'Sentence text/index/origin')
                    empty += not expected
                    check(origin['disposition'] == ('ready' if expected else 'input_unavailable'), 'Availability')
            check(pairs == spec['scheduled_pairs'] == 1500 and annotated == spec['annotated_pairs'] and
                  empty == spec['unavailable_pairs'] and len(actual) == spec['claims'] == 300, 'Recorded counts')
            counts[condition] = dict(claims=len(actual), pairs=pairs, applicable_annotated_pairs=annotated,
                                    empty_inputs=empty, synthetic_sentences=synthetic)
        check(set(counts) == {'primary','rationale_only','evidence_removal','irrelevant_context','constructed_conflict'}, 'All five conditions')
        result.update(status='PASS', conditions=counts, no_import_of_producer_or_transformer=True,
                      actual_model_execution=False, manifest_sha256=args.sha256)
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error))
    result.update(checks=checks, reviewer_sha256=file_hash(__file__))
    with (args.output/'INPUT-REVIEW.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
