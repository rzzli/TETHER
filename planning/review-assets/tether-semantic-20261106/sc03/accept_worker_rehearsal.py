"""Source-inclusive stdlib audit of the actual five-pair fictional worker run."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
ASSETS = ROOT/'planning/review-assets/tether-semantic-20261106/sc03'
OUTPUT = ASSETS/'worker-rehearsal-acceptance01'


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fingerprint(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=False)
    checks = 0
    pins = {}
    def check(ok, reason):
        nonlocal checks
        checks += 1
        if not ok:
            raise ValueError(reason)
    def verify(path, digest):
        check(sha(path) == digest, 'File hash: ' + str(path))
        pins[str(Path(path).resolve())] = digest
    result = dict(status='FAIL')
    try:
        freeze = ASSETS/'worker-rehearsal-freeze01'
        verify(freeze/'MANIFEST.json', '108eb66455d25781a61e8138ebf1379f451db6e4b349f1aa8c7311d3089314ec')
        manifest = read(freeze/'MANIFEST.json')
        for proof in manifest['pins']:
            verify(proof['path'], proof['sha256'])
            check(Path(proof['path']).stat().st_size == proof['bytes'], 'Pinned byte count')
        outcome = read(freeze/'launch/OUTCOME.json')
        check(outcome['status'] == 'completed' and outcome['exit_code'] == 0 and
              outcome['all_frozen_pins_unchanged'] and not outcome['automatic_retry'], 'Successful frozen supervision')
        child = Path(manifest['qualification_output'])
        receipt = read(child/'RECEIPT.json')
        check(receipt['status'] == 'complete', 'Complete receipt')
        for relative, proof in receipt['files'].items():
            verify(child/relative, proof['sha256'])
            check((child/relative).stat().st_size == proof['bytes'], 'Output byte count')
        check(set(p.relative_to(child).as_posix() for p in child.rglob('*') if p.is_file()) ==
              set(receipt['files']) | {'RECEIPT.json','journal.jsonl','events.jsonl'}, 'Exact output inventory')
        previous = '0'*64
        events = []
        for index, line in enumerate((child/'journal.jsonl').read_bytes().splitlines()):
            row = json.loads(line)
            digest = row.pop('sha256')
            check(row['sequence'] == index and row['previous_sha256'] == previous and
                  fingerprint(row) == digest, 'Journal chain')
            events.append(row)
            previous = digest
        check(previous == receipt['journal_last_sha256'] and len(events) == receipt['journal_records'], 'Journal receipt binding')
        for kind in ('pair_started','pair_completed','pair_committed'):
            check(sum(e['event'] == kind for e in events) == 5, 'Five exactly-once pair events: ' + kind)
        request = json.loads((freeze/'fictional-requests.jsonl').read_bytes())
        claim = read(child/'claims/90001.json')
        check(claim['input_sha256'] == fingerprint(request) and claim['status'] == 'produced', 'Claim request binding')
        expected_evidence = {}
        for doc in request['documents']:
            did = doc['doc_id']
            pair = read(child/f'pairs/90001-{did}.json')
            check(pair['input_document_sha256'] == fingerprint(doc) and pair['status'] == 'completed'
                  and pair['model_dispatch'] is True, 'Pair input and status')
            prediction = pair['prediction']
            check(prediction['claim_id'] == 90001 and prediction['abstract_id'] == did, 'Pair identity')
            labels = ['CONTRADICT','NEI','SUPPORT']
            check(prediction['predicted_label'] == labels[max(range(3), key=prediction['label_probs'].__getitem__)], 'Native label decode')
            check(all(type(i) is int and 0 <= i < len(doc['abstract']) for i in prediction['predicted_rationale']), 'Source sentence bounds')
            if prediction['predicted_label'] != 'NEI':
                expected_evidence[str(did)] = dict(label=prediction['predicted_label'], sentences=prediction['predicted_rationale'])
            committed = [e['details'] for e in events if e['event'] == 'pair_committed' and e['details']['abstract_id'] == did]
            check(len(committed) == 1 and committed[0]['sha256'] == sha(child/committed[0]['path']), 'Pair commit journal binding')
        check(claim['prediction'] == dict(id=90001, evidence=expected_evidence), 'Exact five-pair native assembly')
        report = read(child/'REPORT.json')
        check(report['counts'] == dict(scheduled_claims=1, scheduled_pairs=5, completed_claims=1,
            complete_prediction_claims=1, completed_pairs=5, input_unavailable_pairs=0, overlength_pairs=0,
            unexpected_failed_pairs=0), 'Complete measured counts')
        for tree in (child, freeze/'launch'):
            for path in tree.rglob('*'):
                if path.is_file():
                    pins[str(path.resolve())] = sha(path)
        result.update(status='PASS', actual_model_pairs=5, benchmark_predictions=0,
            scope='Actual fictional resident-worker integration; semantic performance established only by separate SC03 evaluation.',
            report=report, receipt_sha256=sha(child/'RECEIPT.json'))
    except BaseException as error:
        result.update(error_type=type(error).__name__, error=str(error))
    result.update(checks=checks, file_pins=pins, reviewer_sha256=sha(__file__))
    with (OUTPUT/'ACCEPTANCE.json').open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=result['status'], checks=checks, error=result.get('error'),
                         sha256=sha(OUTPUT/'ACCEPTANCE.json'))))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
