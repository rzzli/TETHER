"""Pure AI engineering audit; mutate one retained wrapper only in memory.

This checks the native execution verifier component, not full resealed-run replay.
No frozen bundle, accepted code or runtime/resource file is modified.
"""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import os
from pathlib import Path
import time

from asof.agents import Usage
from asof.serde import ContractError, canonical, fingerprint
from asof.study.native_interpretation import verify_native_execution
from asof.study.token_capacity import TrustedTokenCapacity

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / 'data/cache/r09-native-simulation-20261028T012949Z'
CELL = RUN / 'cells/00'
REPORT = HERE / 'NATIVE-DURATION-CONSISTENCY-PROBE.json'
assert not REPORT.exists()
guards = []


def audit(event, args):
    if event in ('subprocess.Popen', 'socket.connect', 'socket.__new__', 'socket.getaddrinfo', 'os.system'):
        guards.append(event)
        raise RuntimeError('Pure component verification only')
    if event == 'open' and args and isinstance(args[0], (str, bytes, os.PathLike)):
        if '\\data\\benchmark\\' in os.path.normcase(os.path.abspath(os.fsdecode(args[0]))):
            raise RuntimeError('Protected outcome payloads excluded')


sys.addaudithook(audit)


def load(path):
    return json.loads(path.read_bytes())


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


paths = [CELL / n for n in ('request.json', 'payload.json', 'configuration.json', 'raw-response.bin', 'report.json')]
paths += [RUN / 'receipt.json', RUN / 'journal.jsonl']
before = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}
assert sha(RUN / 'receipt.json') == 'f74bc1605f78acb78a61f9672d5ce1a611ceaeb663bad6fd879a93605f063e98'
request = load(CELL / 'request.json')
payload = load(CELL / 'payload.json')
configuration = load(CELL / 'configuration.json')
wrapper = load(CELL / 'raw-response.bin')
cell_report = load(CELL / 'report.json')
events = [json.loads(line) for line in (RUN / 'journal.jsonl').read_bytes().splitlines()]
context = next(e['details']['context'] for e in events if e['event'] == 'native_context_qualified')
end = next(e['details']['case_end_monotonic'] for e in events if e['event'] == 'integration_started')
descriptor = configuration['capacity_policy']
policy = TrustedTokenCapacity(RUN / 'quotes/00', **{k: descriptor[k] for k in
    ('receipt_sha256', 'prompt_sha256', 'spec_sha256', 'payload_sha256')})
usage = Usage(**cell_report['measured_usage'])
results = []
for name, elapsed in [('retained_baseline', wrapper['elapsed_seconds']), ('impossible_native_duration', 9999.0)]:
    changed = dict(wrapper, elapsed_seconds=elapsed)
    raw = canonical(changed)
    try:
        verify_native_execution(request, payload, raw, configuration, usage,
            capacity_policy=policy, case_deadline=end, expected_native=context,
            deadline=time.monotonic() + 60)
        verdict = 'accepted'
        error = None
    except ContractError as failure:
        verdict = 'rejected'
        error = str(failure)
    results.append(dict(case=name, wrapper_elapsed_seconds=elapsed, verdict=verdict,
        content_sha256=hashlib.sha256(raw).hexdigest(), error=error))
assert results[0]['verdict'] == 'accepted'
assert results[1]['verdict'] == 'accepted', 'Potential gap was not reproduced'
assert all(sha(ROOT / p) == digest for p, digest in before.items())
assert not guards
report = dict(schema_version=1, role='AI_engineering_review_not_scientific_or_human_review',
    status='reproduced_unreconciled_native_wrapper_duration', scope='verify_native_execution_component_only',
    accepted_run_sha256=before['data/cache/r09-native-simulation-20261028T012949Z/receipt.json'],
    child_budget_seconds=configuration['budget']['max_seconds'], child_report_elapsed_seconds=cell_report['elapsed_seconds'],
    parent_case_seconds=300, cases=results, changed_fields=['native_wrapper.elapsed_seconds'],
    persisted_artifact_mutations=0, original_files_unchanged=before, full_resealed_run_replay_attempted=False,
    actual_model_calls=0, native_servers_started=0, network_calls=0, process_dispatches=0, guard_events=guards,
    qualification='Pure transport verifier accepts a duration exceeding both child and parent limits; does not prove an original execution overran.')
with REPORT.open('x', encoding='utf-8') as stream:
    json.dump(report, stream, indent=2)
print(json.dumps({k: report[k] for k in ('status', 'child_budget_seconds', 'child_report_elapsed_seconds', 'cases')}))
