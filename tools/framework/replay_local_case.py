"""Replay one completed local selection run, with no model server or provider calls."""
import argparse
from pathlib import Path

from asof.agents import ReplayBackend
from asof.artifacts import verify_run, write_run
from asof.chrono import admit_snapshot
from asof.contracts import Case, Snapshot, Category
from asof.journal import RunJournal
from asof.retrieval import RetrievalPolicy, bounded_request
from asof.serde import ContractError, decode, fingerprint, read_json, sha256_file, write_json
from asof.workflow import run_workflow, Budget


class BoundedReplay(ReplayBackend):
    backend_id = 'bounded-local-selection-replay-v1'

    def __init__(self, path, policy):
        super().__init__(path)
        self.policy = policy
        self.provenance = {**self.provenance, 'retrieval_policy': policy,
            'usage_basis': 'recorded original usage, not tokens consumed during replay'}

    def prepare_request(self, request):
        return bounded_request(request, self.policy)


def replay(source, output, expected_receipt):
    # Verify the supplied source run first; never dispatch or recover uncertain attempts.
    verify_run(source, expected_receipt)
    inputs = read_json(source / 'inputs.json'); run = read_json(source / 'run.json')
    if run['status'] != 'completed' or run['backend_id'] != 'local-structured-selection-v1':
        raise ContractError('Replay requires a completed explicit local-model run')
    execution = read_json(source / 'backend-execution.json')
    responses = {}
    for item in execution['attempts']:
        if item['status'] != 'completed':
            raise ContractError('Refusing to replay an uncertain or failed model call')
        category = item['request']['category']
        responses.setdefault(category, []).append({'request_sha256': item['request_sha256'],
            'selection': {'observation_ids': item['selection'], 'usage': item['measured_usage']}})
    journal = RunJournal(output)
    try:
        write_json(output / 'replay.json', {'schema_version': 2, 'responses': responses})
        policy = RetrievalPolicy(**inputs['configuration']['backend_provenance']['config']['retrieval'])
        backend = BoundedReplay(output / 'replay.json', policy)
        case = decode(Case, inputs['case']); snapshot = decode(Snapshot, inputs['snapshot'])
        if case.task != 'T6' or inputs['scorer'] is not None:
            raise ContractError('This bounded development replay is limited to T6 without a scorer')
        store = admit_snapshot(snapshot, case, Path(inputs['snapshot_base']), inputs['catalog_policy'])
        write_json(output / 'request.json', {'replayed_run': str(source.resolve()),
            'original_receipt_sha256': expected_receipt, 'replay_tool_sha256': sha256_file(Path(__file__)),
            'provider_calls': 0, 'model_server_calls': 0})
        journal.append('inputs_archived', request_sha256=fingerprint(read_json(output / 'request.json')))
        result = run_workflow(case, store, backend, budget=decode(Budget, run['budget']),
            disabled=tuple(Category(x) for x in inputs['configuration']['disabled']),
            review_enabled=inputs['configuration']['review_enabled'], journal=journal)
        receipt = write_run(output, result, store, None, journal)
        verified = verify_run(output, receipt)
        for name in ['ledger.json', 'features.json', 'prediction.json']:
            if fingerprint(read_json(output / name)) != fingerprint(read_json(source / name)):
                raise ContractError('Replay differs from original derived output: ' + name)
        return {'status': 'verified_exact_derived_output_replay', 'case_id': case.case_id,
            'output': str(output), 'receipt_sha256': receipt, 'model_server_calls': 0,
            'provider_spend_usd': 0, 'verification': verified,
            'usage_interpretation': 'accounting replays recorded tokens; no inference tokens consumed'}
    finally:
        journal.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--receipt-sha256', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        raise ContractError('Replay report already exists')
    write_json(args.report, replay(args.source, args.output, args.receipt_sha256))
