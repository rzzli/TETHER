"""One bounded, resident-model SC03 condition. No references, retries or scoring."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
from experiments.scifact_comparison.inputs import CONDITIONS, digest, encoded, need, validate_requests
from experiments.scifact_multivers.contracts import ContractError, native_predictions

MAX_INPUT_BYTES = 64 * 1024**2
MAX_OUTPUT_BYTES = 2 * 1024**3


class Writer:
    """Exclusive writes with a total byte cap; terminal failure gets separate 8 KiB."""
    def __init__(self, root, maximum):
        self.root = root
        self.maximum = maximum
        self.bytes = 0
        self.files = {}
        self.previous = '0'*64
        self.sequence = 0
        self.journal = (root/'journal.jsonl').open('xb', buffering=0)
        self.events = (root/'events.jsonl').open('xb', buffering=0)

    def reserve(self, raw):
        if self.bytes + len(raw) > self.maximum:
            raise OSError('Condition output byte budget exceeded')
        self.bytes += len(raw)

    def publish(self, relative, value):
        raw = encoded(value) + b'\n'
        self.reserve(raw)
        path = self.root/relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        self.files[relative] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

    def event(self, event, **details):
        row = dict(sequence=self.sequence, previous_sha256=self.previous,
                   event=event, monotonic_seconds=time.monotonic(), details=details)
        fingerprint = digest(row)
        raw = encoded(dict(row, sha256=fingerprint)) + b'\n'
        self.reserve(raw)
        self.journal.write(raw)
        self.previous = fingerprint
        self.sequence += 1

    def signal(self, event, **details):
        raw = encoded(dict(event=event, monotonic_seconds=time.monotonic(), **details)) + b'\n'
        self.reserve(raw)
        self.events.write(raw)

    def close(self):
        self.journal.close()
        self.events.close()


def checked_bytes(path, expected, maximum):
    path = Path(path)
    need(not path.is_symlink() and path.is_file(), 'Regular input file required')
    with path.open('rb') as stream:
        raw = stream.read(maximum+1)
    need(len(raw) <= maximum, 'Input byte cap exceeded')
    need(hashlib.sha256(raw).hexdigest() == expected, 'Input SHA256 differs')
    return raw


def process_requests(requests, solver, writer, condition, *, pair_seconds=120, expected_k=5):
    """Injected solver is for fictional tests; CLI always constructs the pinned model."""
    validate_requests(requests, expected_k=expected_k)
    counts = dict(scheduled_claims=len(requests), scheduled_pairs=len(requests)*expected_k,
                  completed_claims=0, complete_prediction_claims=0, completed_pairs=0,
                  input_unavailable_pairs=0, overlength_pairs=0, unexpected_failed_pairs=0)
    for request in requests:
        cid = request['id']
        start, cpu = time.perf_counter(), time.process_time()
        writer.signal('case_started', case_id=str(cid))
        writer.event('claim_started', claim_id=cid, input_sha256=digest(request), condition=condition)
        pairs = []
        for doc in request['documents']:
            did = doc['doc_id']
            path = f'pairs/{cid}-{did}.json'
            record = dict(claim_id=cid, abstract_id=did, input_document_sha256=digest(doc),
                          prediction=None, observations=None)
            if not doc['abstract']:
                record.update(status='input_unavailable', reason='No abstract sentences remain after intervention',
                              model_dispatch=False)
                counts['input_unavailable_pairs'] += 1
                writer.event('pair_unavailable', claim_id=cid, abstract_id=did, reason=record['reason'])
            else:
                # The model's own pair event records the potential dispatch before tokenization.
                def model_event(**event):
                    kind = event.pop('event')
                    event.pop('monotonic_seconds', None)
                    writer.event(kind, **event)
                try:
                    answer = solver.predict([dict(id=cid, claim=request['claim'], doc_ids=[did])], [doc],
                                            pair_deadline_seconds=pair_seconds, event=model_event)
                    need(answer['status'] == 'completed' and len(answer['pair_predictions']) == 1 and
                         len(answer['observations']) == 1, 'Solver output count/status differs')
                    pair = answer['pair_predictions'][0]
                    need(pair['claim_id'] == cid and pair['abstract_id'] == did, 'Solver replaced requested pair')
                    record.update(status='completed', prediction=pair, observations=answer['observations'][0],
                                  model_dispatch=True)
                    counts['completed_pairs'] += 1
                except ContractError as error:
                    # This exact adapter rejection happens before forward; all other contract errors stop.
                    if str(error) != 'Input exceeds 4096 tokens; no truncation is permitted':
                        counts['unexpected_failed_pairs'] += 1
                        raise
                    record.update(status='overlength', reason=str(error), model_dispatch=False)
                    counts['overlength_pairs'] += 1
                except BaseException:
                    counts['unexpected_failed_pairs'] += 1
                    raise
            writer.publish(path, record)
            writer.event('pair_committed', claim_id=cid, abstract_id=did, status=record['status'],
                         path=path, sha256=writer.files[path]['sha256'])
            pairs.append(record)
        complete = all(p['status'] == 'completed' for p in pairs)
        prediction = native_predictions([cid], [p['prediction'] for p in pairs])[0] if complete else None
        result = dict(schema_version=1, condition=condition, id=cid, input_sha256=digest(request),
                      status='produced' if complete else 'incomplete', prediction=prediction,
                      pairs=[dict(abstract_id=p['abstract_id'], status=p['status'],
                                  path=f'pairs/{cid}-{p["abstract_id"]}.json') for p in pairs],
                      wall_seconds=time.perf_counter()-start, cpu_seconds=time.process_time()-cpu)
        writer.publish(f'claims/{cid}.json', result)
        writer.event('claim_committed', claim_id=cid, status=result['status'],
                     path=f'claims/{cid}.json', sha256=writer.files[f'claims/{cid}.json']['sha256'])
        writer.signal('case_completed', case_id=str(cid), status='accounted', prediction_status=result['status'])
        counts['completed_claims'] += 1
        counts['complete_prediction_claims'] += int(complete)
    return counts


def run(recipe_path, recipe_sha256, output):
    output = Path(output).resolve()
    need(output.is_relative_to(ROOT) and output != ROOT, 'Output must be in workspace')
    output.mkdir(parents=True, exist_ok=False)
    writer = Writer(output, MAX_OUTPUT_BYTES)
    started, cpu = time.perf_counter(), time.process_time()
    try:
        writer.signal('started')
        recipe_raw = checked_bytes(recipe_path, recipe_sha256, 1024*1024)
        recipe = json.loads(recipe_raw)
        need(set(recipe) == {'schema_version','kind','condition','requests','schedule','acquisition_root',
                             'acquisition_receipt_sha256','device','pair_seconds','output_bytes'}, 'Recipe fields differ')
        need(recipe['schema_version'] == 1 and recipe['kind'] == 'sc03_condition_worker', 'Recipe kind differs')
        need(recipe['condition'] in CONDITIONS and recipe['device'] == 'cuda:0', 'Condition/device differs')
        need(type(recipe['pair_seconds']) is int and 0 < recipe['pair_seconds'] <= 120, 'Pair deadline differs')
        need(recipe['output_bytes'] == MAX_OUTPUT_BYTES, 'Output cap differs')
        writer.publish('recipe.json', recipe)
        proof = recipe['requests']
        need(set(proof) == {'path','sha256','bytes'}, 'Request proof fields differ')
        raw = checked_bytes(proof['path'], proof['sha256'], MAX_INPUT_BYTES)
        need(len(raw) == proof['bytes'], 'Request length differs')
        requests = [json.loads(line) for line in raw.splitlines()]
        validate_requests(requests, expected_schedule=recipe['schedule'])
        writer.event('inputs_admitted', requests_sha256=proof['sha256'], input_bytes=len(raw),
                     condition=recipe['condition'], references_read=False)
        from experiments.scifact_multivers.inference import LoadedSolver
        from experiments.scifact_multivers.runtime import process_memory
        writer.signal('model_load_started')
        solver = LoadedSolver(recipe['acquisition_root'], recipe['acquisition_receipt_sha256'], device=recipe['device'])
        writer.publish('MODEL.json', dict(metadata=solver.metadata, device=solver.device_info,
                                        load_seconds=solver.load_seconds))
        writer.signal('models_loaded')
        counts = process_requests(requests, solver, writer, recipe['condition'], pair_seconds=recipe['pair_seconds'])
        writer.publish('REPORT.json', dict(status='schedule_accounted', counts=counts,
            wall_seconds=time.perf_counter()-started, cpu_seconds=time.process_time()-cpu,
            memory=process_memory(), load_seconds=solver.load_seconds, provider_cost_usd=0,
            output_bytes_before_report=writer.bytes, scientific_scoring_performed=False))
        writer.event('condition_completed', counts=counts)
        # Receipt binds the scientific files; the supervisor separately retains the events and sources.
        writer.publish('RECEIPT.json', dict(status='complete', files=dict(writer.files),
            journal_last_sha256=writer.previous, journal_records=writer.sequence,
            recipe_sha256=recipe_sha256, requests_sha256=proof['sha256']))
        writer.signal('completed', status='passed')
        print(json.dumps(dict(status='schedule_accounted', counts=counts)))
    except BaseException as error:
        # Separate bounded terminal reserve survives a scientific-output budget failure.
        raw = encoded(dict(status='failed', error_type=type(error).__name__, error=str(error)[:2000],
                           automatic_retry=False, recovery='Inspect durable pair files and journal; never repeat an uncertain call.'))+b'\n'
        if len(raw) <= 8192:
            with (output/'FAILED.json').open('xb') as stream:
                stream.write(raw)
        raise
    finally:
        writer.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--recipe', required=True)
    parser.add_argument('--recipe-sha256', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    run(args.recipe, args.recipe_sha256, args.output)
