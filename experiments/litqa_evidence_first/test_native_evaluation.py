"""Invented HTTP records exercise the actual new cell and independent reader."""
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, encode
from experiments.labbench.tests import test_model as model_fixtures
from experiments.litqa_refinement import test_native_evaluation as fixtures
from . import cells, contracts as c, model, native_evaluation as e, transport


class NativeTests(unittest.TestCase):
    def setUp(self):
        fixtures.NativeEvaluationTests.setUp(self)
        self.f.root = self.f.root.resolve()
        self.f.f.root = self.f.f.root.resolve()
        self.method = c.write(self.f.root.resolve() / 'METHOD.json', model.method_descriptor())

    def cell(self, task='repair', raw=None, sources=None, mutate_body=None):
        root = self.f.root / task
        sources = self.sources if sources is None and task == 'repair' else ([] if sources is None else sources)
        pair = model.make_pair(self.q, self.prior, self.critic, sources, self.f.f.model)
        member = pair[task]; self.f.f.payload = member['payload']
        self.f.f.request = member['request']
        decoded = dict(answer_index=0, evidence_ids=['fixture:p1'] if sources else [])
        body = self.f.f.native_body(content=canonical(decoded).decode() if raw is None else raw)
        if mutate_body is not None: body = mutate_body(body)
        with patch.object(transport.native, '_check_owner', return_value=12345), \
             patch.object(transport.native, '_watchdog', return_value=model_fixtures.Timer()), \
             patch.object(transport.mcq, 'tokenize_once', side_effect=lambda *a, **k: fixtures.tokenize(self.f, *a, **k)), \
             self.f.f.transport(model_fixtures.Response(body)):
            cells.call_pair_member(self.q, self.prior, self.critic, sources, self.f.f.model, member, task,
                owner=self.f.f.owner, output=root, deadline=time.monotonic() + 15,
                alias=self.f.alias, execution_id='invented-' + task, control_sha256=pair['control_sha256'])
        return root, e.n.load(root / 'INPUT.json')

    def read(self, root, inputs):
        return e.reconstruct_cell(root, inputs, execution_id='invented-' + inputs['task'],
            model_provenance=self.f.f.model, alias=self.f.alias, owner_pid=12345,
            endpoint='http://127.0.0.1:' + str(self.f.f.spec.port), method_proof=self.method)

    def test_both_tasks_independently_reconstruct_raw_capture(self):
        for task in ('repair', 'removal'):
            root, inputs = self.cell(task)
            got = self.read(root, inputs)
            self.assertEqual(got['summary']['status'], 'completed')
            self.assertEqual(got['summary']['usage'], dict(input_tokens=50, output_tokens=12, cost_usd=0))
            self.assertFalse(got['source_lineage_checked'])
            self.assertEqual(got['sources'], self.sources if task == 'repair' else [])

    def test_complete_bad_codec_preserves_measured_usage_without_retry(self):
        root, inputs = self.cell(raw='malformed')
        got = self.read(root, inputs)
        self.assertEqual(got['summary']['status'], 'codec_failure')
        self.assertIsNone(got['summary']['decoded'])
        self.assertEqual(got['summary']['usage']['output_tokens'], 12)
        with self.assertRaises(FileExistsError): self.cell()
        self.assertEqual(len(self.f.f.calls), 1)

    def test_independent_prompt_rejects_added_wrapper_text(self):
        pair = model.make_pair(self.q, self.prior, self.critic, self.sources, self.f.f.model)
        for task in ('repair', 'removal'):
            got = e.prepare_member(task, self.q, self.prior, self.critic,
                self.sources if task == 'repair' else [], self.f.f.model, self.method)
            self.assertEqual(canonical(got), canonical(pair[task]))
        root, inputs = self.cell()
        value = e.n.load(root / 'native/payload.json'); value['prompt'] += 'wrapper metadata'
        (root / 'native/payload.json').write_bytes(canonical(value))
        with self.assertRaises(ValueError): self.read(root, inputs)

    def test_reader_does_not_call_producer_codec(self):
        root, inputs = self.cell()
        with patch.object(model, 'make_request', side_effect=AssertionError('producer replay forbidden')):
            self.assertEqual(self.read(root, inputs)['summary']['status'], 'completed')

    def test_changed_summary_usage_or_request_identity_fails(self):
        root, inputs = self.cell()
        value = e.n.load(root / 'SUMMARY.json'); value['usage']['input_tokens'] += 1
        (root / 'SUMMARY.json').write_bytes(canonical(value))
        with self.assertRaises(ValueError): self.read(root, inputs)

    def test_removal_rejects_factual_member_before_dispatch(self):
        pair = model.make_pair(self.q, self.prior, self.critic, self.sources, self.f.f.model)
        with self.assertRaises(ValueError):
            cells.call_pair_member(self.q, self.prior, self.critic, [], self.f.f.model, pair['repair'], 'removal',
                owner=None, output=self.f.root / 'bad-removal', deadline=time.monotonic() + 10,
                alias=self.f.alias, execution_id='invented-removal', control_sha256=pair['control_sha256'])
        self.assertFalse(self.f.f.calls)
        self.assertTrue((self.f.root / 'bad-removal/FAILURE.json').exists())

    def test_modified_method_proof_fails(self):
        root, inputs = self.cell()
        value = encode(model.method_descriptor()); value['additional_model_calls'] = 1
        (self.f.root / 'METHOD.json').write_bytes(canonical(value))
        with self.assertRaises(ValueError): self.read(root, inputs)

    def test_completion_limit_is_terminal_and_never_codec_failure(self):
        import json
        def altered(raw):
            body = json.loads(raw); body.update(stop_type='limit', stop=True, tokens_predicted=256)
            return canonical(body)
        with self.assertRaises(ValueError): self.cell(mutate_body=altered)
        self.assertFalse((self.f.root / 'repair/SUMMARY.json').exists())
        self.assertTrue((self.f.root / 'repair/FAILURE.json').exists())
        self.assertEqual(len(self.f.f.calls), 1)


if __name__ == '__main__': unittest.main()
