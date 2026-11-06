import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.scifact_comparison.inputs import digest
from experiments.scifact_comparison.worker import Writer, checked_bytes, process_requests, run
from experiments.scifact_multivers.contracts import ContractError


class FakeSolver:
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def predict(self, claims, corpus, *, pair_deadline_seconds, event):
        self.calls += 1
        cid, did = claims[0]['id'], corpus[0]['doc_id']
        event(event='pair_started', claim_id=cid, abstract_id=did)
        if self.error:
            raise self.error
        prediction = dict(claim_id=cid, abstract_id=did, predicted_label='SUPPORT',
                          predicted_rationale=[0], label_probs=[0.,0.,1.], rationale_probs=[1.])
        event(event='pair_completed', claim_id=cid, abstract_id=did, prediction=prediction)
        return dict(status='completed', pair_predictions=[prediction], observations=[dict(token_count=10)])


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.writer = Writer(self.root, 1024*1024)
        self.addCleanup(self.writer.close)
        self.requests = [dict(id=1, claim='Fictional claim.', documents=[dict(doc_id=2, title='Title', abstract=['Sentence.'])])]

    def process(self, solver):
        return process_requests(self.requests, solver, self.writer, 'primary', expected_k=1)

    def test_complete_commits_before_case_terminal(self):
        counts = self.process(FakeSolver())
        self.assertEqual(counts['completed_pairs'], 1)
        result = json.loads((self.root/'claims/1.json').read_bytes())
        self.assertEqual(result['prediction']['evidence']['2']['sentences'], [0])
        events = [json.loads(line) for line in (self.root/'events.jsonl').read_bytes().splitlines()]
        self.assertEqual([e['event'] for e in events], ['case_started','case_completed'])
        self.assertTrue((self.root/'pairs/1-2.json').is_file())

    def test_hash_chain_reconstructs(self):
        self.process(FakeSolver())
        previous = '0'*64
        for i, line in enumerate((self.root/'journal.jsonl').read_bytes().splitlines()):
            row = json.loads(line)
            actual = row.pop('sha256')
            self.assertEqual((row['sequence'], row['previous_sha256']), (i, previous))
            self.assertEqual(digest(row), actual)
            previous = actual

    def test_empty_has_no_dispatch_or_nei(self):
        self.requests[0]['documents'][0]['abstract'] = []
        solver = FakeSolver()
        counts = self.process(solver)
        self.assertEqual(solver.calls, 0)
        self.assertEqual(counts['input_unavailable_pairs'], 1)
        self.assertIsNone(json.loads((self.root/'claims/1.json').read_bytes())['prediction'])

    def test_exact_actual_overlength_is_accounted(self):
        counts = self.process(FakeSolver(ContractError('Input exceeds 4096 tokens; no truncation is permitted')))
        self.assertEqual(counts['overlength_pairs'], 1)
        pair = json.loads((self.root/'pairs/1-2.json').read_bytes())
        self.assertFalse(pair['model_dispatch'])
        self.assertIsNone(pair['prediction'])

    def test_other_contract_error_stops(self):
        solver = FakeSolver(ContractError('Corrupt weights'))
        with self.assertRaisesRegex(ContractError, 'Corrupt'):
            self.process(solver)
        self.assertEqual(solver.calls, 1)
        self.assertFalse((self.root/'claims/1.json').exists())

    def test_timeout_and_interruption_not_retried(self):
        for error in (TimeoutError('slow'), KeyboardInterrupt()):
            solver = FakeSolver(error)
            with self.assertRaises(type(error)):
                self.process(solver)
            self.assertEqual(solver.calls, 1)
        events = [json.loads(line) for line in (self.root/'events.jsonl').read_bytes().splitlines()]
        self.assertFalse(any(e['event'] == 'case_completed' for e in events))

    def test_write_failure_has_no_success_event(self):
        original = self.writer.publish
        def failed(relative, value):
            if relative.startswith('pairs/'):
                raise OSError('injected disk failure')
            return original(relative, value)
        with patch.object(self.writer, 'publish', failed):
            with self.assertRaisesRegex(OSError, 'disk failure'):
                self.process(FakeSolver())
        events = [json.loads(line) for line in (self.root/'events.jsonl').read_bytes().splitlines()]
        self.assertEqual([r['event'] for r in events], ['case_started'])

    def test_output_budget(self):
        self.writer.maximum = 3
        with self.assertRaisesRegex(OSError, 'byte budget'):
            self.process(FakeSolver())
        self.assertFalse((self.root/'claims/1.json').exists())

    def test_exclusive_writer_rejects_existing(self):
        self.writer.publish('one.json', dict(a=1))
        with self.assertRaises(FileExistsError):
            self.writer.publish('one.json', dict(a=2))
        self.assertEqual(json.loads((self.root/'one.json').read_bytes()), dict(a=1))

    def test_duplicate_worker_destination_never_loads_model(self):
        # Workspace temp paths are configured by the qualification controller.
        with self.assertRaises(FileExistsError):
            run('nonexistent-recipe', '0'*64, self.root)

    def test_inputs_hash_and_size_cap(self):
        path = self.root/'source.txt'
        path.write_bytes(b'fictional')
        import hashlib
        sha = hashlib.sha256(b'fictional').hexdigest()
        self.assertEqual(checked_bytes(path, sha, 9), b'fictional')
        with self.assertRaisesRegex(ValueError, 'byte cap'):
            checked_bytes(path, sha, 8)
        with self.assertRaisesRegex(ValueError, 'SHA256'):
            checked_bytes(path, '0'*64, 9)

    def test_annotations_rejected_before_solver(self):
        self.requests[0]['reference'] = 'SUPPORT'
        solver = FakeSolver()
        with self.assertRaisesRegex(ValueError, 'annotations'):
            self.process(solver)
        self.assertEqual(solver.calls, 0)


if __name__ == '__main__':
    unittest.main()
