"""Reconstruct completed worker outputs from receipts, inputs and durable events."""
import hashlib
import json
from pathlib import Path

from experiments.scifact_comparison.inputs import digest, need, validate_requests
from experiments.scifact_comparison.policy import validate_pair_decode
from experiments.scifact_multivers.contracts import native_predictions


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):
    def pairs(items):
        result = {}
        for key,value in items:
            need(key not in result,'Duplicate JSON key')
            result[key] = value
        return result
    with Path(path).open('rb') as stream:
        raw = stream.read(64*1024**2+1)
    need(len(raw) <= 64*1024**2,'Audit input exceeds bound')
    return json.loads(raw,object_pairs_hook=pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON constant')))


def journal(root, receipt):
    previous = '0'*64
    events = []
    with (root/'journal.jsonl').open('rb') as stream:
        for index,line in enumerate(stream):
            need(len(line) <= 1024**2,'Oversized journal event')
            row = json.loads(line)
            observed = row.pop('sha256')
            need(row['sequence'] == index and row['previous_sha256'] == previous and digest(row) == observed,
                 'Journal hash chain differs')
            previous = observed
            events.append(row)
    need(previous == receipt['journal_last_sha256'] and len(events) == receipt['journal_records'],
         'Receipt does not bind terminal journal')
    return events


def verify_outputs(root, receipt_sha256, requests, *, expected_condition, expected_k=5):
    root = Path(root)
    schedule = validate_requests(requests,expected_k=expected_k)
    need(file_sha(root/'RECEIPT.json') == receipt_sha256,'Worker receipt external anchor differs')
    receipt = read(root/'RECEIPT.json')
    need(receipt['status'] == 'complete','Worker not completed')
    files = receipt['files']
    for relative,proof in files.items():
        path = (root/relative).resolve()
        need(path.is_relative_to(root.resolve()) and not Path(relative).is_absolute(), 'Output proof escapes worker root')
        need(path.is_file() and not path.is_symlink() and file_sha(path) == proof['sha256'] and
             path.stat().st_size == proof['bytes'],'Sealed output bytes differ')
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
    need(actual == set(files) | {'RECEIPT.json','journal.jsonl','events.jsonl'},'Worker output inventory differs')
    recipe = read(root/'recipe.json')
    need(recipe['condition'] == expected_condition and recipe['schedule'] == schedule,'Frozen recipe condition/schedule differs')
    need(receipt['recipe_sha256'] == file_sha(root/'recipe.json'),'Receipt recipe binding differs')
    raw_requests = b''.join(json.dumps(r,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()+b'\n' for r in requests)
    need(hashlib.sha256(raw_requests).hexdigest() == receipt['requests_sha256'] == recipe['requests']['sha256'],
         'Receipt request bytes differ')
    events = journal(root,receipt)
    indexed = {}
    for row in events:
        details = row['details']
        indexed.setdefault((row['event'],details.get('claim_id'),details.get('abstract_id')),[]).append(details)
    def one(kind,cid=None,did=None):
        matches = indexed.get((kind,cid,did),[])
        need(len(matches) == 1,'Missing/duplicate event: '+str((kind,cid,did)))
        return matches[0]
    admitted = one('inputs_admitted')
    need(admitted['requests_sha256'] == receipt['requests_sha256'] and
         admitted['condition'] == expected_condition and admitted['references_read'] is False,'Input admission journal differs')
    model = read(root/'MODEL.json')
    need(model['metadata']['hparams'].get('label_threshold') is None and
         model['metadata']['hparams']['rationale_threshold'] == .5,'Qualified decoding configuration differs')
    counts = dict(scheduled_claims=len(schedule),scheduled_pairs=len(schedule)*expected_k,
        completed_claims=0,complete_prediction_claims=0,completed_pairs=0,input_unavailable_pairs=0,
        overlength_pairs=0,unexpected_failed_pairs=0)
    claims,all_pairs = [],{}
    expected_files = {'recipe.json','MODEL.json','REPORT.json'}
    for request in requests:
        cid = request['id']
        need(one('claim_started',cid)['input_sha256'] == digest(request),'Claim start input binding')
        pairs = []
        for doc in request['documents']:
            did = doc['doc_id']
            relative = f'pairs/{cid}-{did}.json'
            expected_files.add(relative)
            pair = read(root/relative)
            need(pair['claim_id'] == cid and pair['abstract_id'] == did and
                 pair['input_document_sha256'] == digest(doc),'Pair input identity differs')
            committed = one('pair_committed',cid,did)
            need(committed['path'] == relative and committed['sha256'] == files[relative]['sha256'] and
                 committed['status'] == pair['status'],'Pair commit differs from artifact')
            if pair['status'] == 'completed':
                one('pair_started',cid,did)
                completed = one('pair_completed',cid,did)
                need(pair['model_dispatch'] is True and completed['prediction'] == pair['prediction'],
                     'Pair result differs from execution event')
                need(pair['prediction']['claim_id'] == cid and pair['prediction']['abstract_id'] == did,'Prediction identity differs')
                validate_pair_decode(pair['prediction'],len(doc['abstract']))
                need(all(completed[k] == v for k,v in pair['observations'].items()),'Measured observations differ from events')
                counts['completed_pairs'] += 1
            elif pair['status'] == 'input_unavailable':
                need(not doc['abstract'] and pair['prediction'] is None and pair['model_dispatch'] is False,
                     'Unavailable input fabricated a prediction')
                one('pair_unavailable',cid,did)
                need(not indexed.get(('pair_started',cid,did)),'Empty input dispatched')
                counts['input_unavailable_pairs'] += 1
            elif pair['status'] == 'overlength':
                one('pair_started',cid,did)
                failed = one('pair_failed',cid,did)
                need(failed['error'] == pair['reason'] == 'Input exceeds 4096 tokens; no truncation is permitted'
                     and pair['prediction'] is None and pair['model_dispatch'] is False,'Invalid overlength disposition')
                counts['overlength_pairs'] += 1
            else:
                raise ValueError('Unexpected pair status in completed worker')
            pairs.append(pair)
        relative = f'claims/{cid}.json'
        expected_files.add(relative)
        claim = read(root/relative)
        complete = all(p['status'] == 'completed' for p in pairs)
        need(claim['id'] == cid and claim['condition'] == expected_condition and
             claim['input_sha256'] == digest(request),'Claim source binding differs')
        expected = native_predictions([cid],[p['prediction'] for p in pairs])[0] if complete else None
        need(claim['prediction'] == expected and claim['status'] == ('produced' if complete else 'incomplete'),
             'Claim prediction/operational state differs')
        need(claim['pairs'] == [dict(abstract_id=p['abstract_id'],status=p['status'],path=f'pairs/{cid}-{p["abstract_id"]}.json') for p in pairs],
             'Claim pair inventory differs')
        committed = one('claim_committed',cid)
        need(committed['path'] == relative and committed['sha256'] == files[relative]['sha256']
             and committed['status'] == claim['status'],'Claim commit differs')
        claims.append(claim)
        all_pairs[cid] = pairs
        counts['completed_claims'] += 1
        counts['complete_prediction_claims'] += int(complete)
    need(set(files) == expected_files,'Receipt contains missing or unexpected scientific artifacts')
    report = read(root/'REPORT.json')
    need(report['status'] == 'schedule_accounted' and report['counts'] == counts == one('condition_completed')['counts'],
         'Measured accounting contradicts events/results')
    # Reject extra or reordered completed/start events, including hidden extra calls.
    expected_pairs = [(r['id'],d['doc_id']) for r in requests for d in r['documents'] if d['abstract']]
    actual_pairs = [(r['details']['claim_id'],r['details']['abstract_id']) for r in events if r['event'] == 'pair_started']
    need(actual_pairs == expected_pairs,'Unexpected/reordered dispatched pairs')
    allowed_kinds = {'inputs_admitted','claim_started','pair_started','pair_completed','pair_failed',
                     'pair_unavailable','pair_committed','claim_committed','condition_completed'}
    need(all(r['event'] in allowed_kinds for r in events),'Unknown journal event')
    return dict(status='verified',counts=counts,claims=claims,pairs=all_pairs,report=report,
                model=model,receipt_sha256=receipt_sha256)
