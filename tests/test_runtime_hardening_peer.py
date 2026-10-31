"""Independent workflow boundary regressions using only fake local transport."""
from collections import Counter
from dataclasses import replace
from datetime import date
import io
from pathlib import Path
import tempfile
import unittest
import urllib.error

from asof.archive.core import observation_exclusion as archived_observation_exclusion
from asof.artifacts import verify_run, write_run
from asof.chrono import load_snapshot, observation_exclusion
from asof.contracts import Case, Category
from asof.journal import RunJournal
from asof.local_model import LocalSelectionBackend
from asof.provenance import InputGraph
from asof.serde import canonical, decode, encode, read_json, write_json
from asof.workflow import Budget, run_workflow


FIXTURE = Path(__file__).resolve().parents[1] / 'src/asof/demo/v2'


class FailingTransport:
    def __init__(self, error=None, response=None):
        self.calls = []
        self.error = error
        self.response = response

    def open(self, request, timeout):
        self.calls.append((request, timeout))
        if self.error is not None:
            raise self.error
        return io.BytesIO(canonical(self.response))


class RuntimeHardeningPeerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.case = decode(Case, read_json(FIXTURE/'case.json'))
        self.store = load_snapshot(FIXTURE/'snapshot.json', self.case)
        self.config = dict(schema_version=1, endpoint='http://127.0.0.1:55580',
            model_id='fake-transport-only', model_provenance=dict(
                weights_sha256={'fixture': 'a'*64}, runtime_sha256='b'*64),
            retrieval=dict(max_records=12, max_request_bytes=12000),
            max_output_tokens=256, timeout_seconds=2, seed=20261026)
        self.config_path = self.root/'config.json'
        write_json(self.config_path, self.config)

    def execute(self, transport):
        backend = LocalSelectionBackend(self.config_path)
        backend.opener = transport
        output = self.root/'run'
        journal = RunJournal(output)
        try:
            # Headroom keeps the test about failure policy, not unrelated exhaustion.
            # Extra review retries are available but must never retry a failed call.
            budget = Budget(max_input_tokens=200000, max_retries=3)
            result = run_workflow(self.case, self.store, backend, budget=budget, journal=journal)
            write_json(output/'backend-execution.json', dict(schema_version=1, attempts=backend.records))
            receipt = write_run(output, result, self.store, None, journal)
        finally:
            journal.close()
        verified = verify_run(output, receipt)
        self.assertEqual(verified['semantic_consistency'], 'verified')
        self.assertEqual(verified['source_binding'], 'current_originals')
        return result, backend

    def assert_failure_accounting(self, result, backend, expected_status):
        trace = encode(result.trace)
        dispatches = [event['details'] for event in trace if event['event'] == 'dispatch']
        accounts = [event['details'] for event in trace if event['event'] == 'attempt_accounted']
        self.assertEqual(result.status, expected_status)
        self.assertEqual(result.calls, len(backend.opener.calls))
        self.assertEqual(result.calls, len(backend.records))
        self.assertEqual(result.calls, len(dispatches))
        self.assertEqual(result.calls, len(accounts))
        self.assertTrue(all(count == 1 for count in Counter(d['category'] for d in dispatches).values()))
        self.assertTrue(all(d['attempt'] == 1 for d in dispatches))
        self.assertEqual({d['attempt_id'] for d in dispatches}, {a['attempt_id'] for a in accounts})
        self.assertTrue(all(a['basis'] == 'quoted_upper_bound_not_measured' for a in accounts))
        self.assertEqual(result.measured_usage.input_tokens, 0)
        self.assertEqual(result.measured_usage.output_tokens, 0)
        self.assertEqual(result.estimated_usage.input_tokens, sum(d['reserved']['input_tokens'] for d in dispatches))
        self.assertEqual(result.estimated_usage.output_tokens, sum(d['reserved']['output_tokens'] for d in dispatches))
        self.assertGreater(result.estimated_usage.input_tokens, 0)
        self.assertEqual(result.usage.cost_usd, 0)
        self.assertTrue(all(r['status'] == 'failed' and 'measured_usage' not in r for r in backend.records))
        self.assertIsNone(result.prediction.probability)

    def assert_continued_categories(self, result):
        ready = [step.category for step in result.plan if step.initial_status == 'ready']
        self.assertGreater(len(ready), 1)
        self.assertEqual(result.calls, len(ready))
        self.assertTrue(all(result.coverage[category.value]['status'] == 'failed' for category in ready))

    def test_url_error_continues_categories_without_retry_and_seals_accounting(self):
        result, backend = self.execute(FailingTransport(urllib.error.URLError('fixture unavailable')))
        self.assert_failure_accounting(result, backend, 'partial')
        self.assert_continued_categories(result)
        self.assertTrue(all(r['error_class'] == 'URLError' for r in backend.records))
        self.assertTrue(all(e['details']['error_class'] == 'ConnectionError'
                            for e in result.trace if e['event'] == 'backend_failed'))

    def test_http_error_continues_categories_without_retry_and_seals_accounting(self):
        error = urllib.error.HTTPError('http://127.0.0.1:55580/completion', 503, 'fixture unavailable', {}, None)
        result, backend = self.execute(FailingTransport(error))
        self.assert_failure_accounting(result, backend, 'partial')
        self.assert_continued_categories(result)
        self.assertTrue(all(r['error_class'] == 'HTTPError' for r in backend.records))

    def test_malformed_response_continues_with_conservative_not_measured_usage(self):
        malformed = dict(truncated=False, tokens_evaluated=2, tokens_predicted=1)
        result, backend = self.execute(FailingTransport(response=malformed))
        self.assert_failure_accounting(result, backend, 'partial')
        self.assert_continued_categories(result)
        self.assertTrue(all(r['error_class'] == 'ContractError' and r['response'] == malformed
                            for r in backend.records))

    def test_unexpected_oserror_is_fatal_after_one_accounted_call(self):
        result, backend = self.execute(FailingTransport(OSError('fixture unexpected IO failure')))
        self.assert_failure_accounting(result, backend, 'failed')
        self.assertEqual(result.calls, 1)
        ready = [step.category for step in result.plan if step.initial_status == 'ready']
        self.assertGreater(len(ready), 1)
        self.assertEqual(result.coverage[ready[0].value]['status'], 'failed')
        self.assertTrue(all(result.coverage[category.value]['status'] == 'not_run' for category in ready[1:]))
        self.assertEqual(backend.records[0]['error_class'], 'OSError')

    def test_archived_publication_policy_preserves_old_inconsistent_metadata_result(self):
        record = self.store.query(self.case, Category.GENETICS)[0]
        observation = replace(record.observation,
            publication_date=date(self.case.origin.year - 1, 1, 1),
            publication_year=self.case.origin.year)
        graph = InputGraph(self.store.snapshot, FIXTURE, None)
        artifact = next(a for a in self.store.snapshot.artifacts if a.artifact_id == record.citation.artifact_id)
        self.assertIsNone(archived_observation_exclusion(observation, artifact, graph, self.case))
        self.assertEqual(observation_exclusion(observation, artifact, graph, self.case),
                         'publication_metadata_inconsistent')
        for exact, year in ((None, self.case.origin.year), (None, None)):
            stable = replace(observation, publication_date=exact, publication_year=year)
            self.assertIsNone(archived_observation_exclusion(stable, artifact, graph, self.case))
            self.assertIsNone(observation_exclusion(stable, artifact, graph, self.case))


if __name__ == '__main__':
    unittest.main()
