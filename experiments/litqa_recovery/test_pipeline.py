"""Recovered full-schedule answering uses fictional captured native responses."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from tether_engine.serde import canonical, encode
from experiments.litqa_comparison.tests import test_replay as native_fixtures
from experiments.litqa_recovery import admission, pipeline as p
from experiments.litqa_recovery import test_collection as source_fixtures


class RecoveryAnswerTests(unittest.TestCase):
    def setUp(self):
        self.source = source_fixtures.RecoveredCollectionTests('runTest')
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        result, _ = self.source.execute()
        self.prepared = admission.prepare(self.source.output, result['receipt']['sha256'], self.source.top)
        self.native = native_fixtures.ReplayTests('runTest')
        self.native.setUp()
        self.addCleanup(self.native.doCleanups)
        self.output = self.source.top / 'answers'
        self.queries = encode(self.prepared.queries)
        self.hints = encode(self.prepared.hints)
        self.cutoff = datetime.now(timezone.utc) + timedelta(minutes=1)

    def answer(self, **changes):
        args = dict(seconds=180, cutoff=self.cutoff, model_provenance=self.native.info['provenance'],
                    call_model=self.native.call)
        args.update(changes)
        return p.answer(self.queries, self.hints, self.prepared, self.output, **args)

    def replay(self):
        sha = p.primary.proof(self.output / 'STAGE-RECEIPT.json')['sha256']
        return p.replay_answers(self.output, sha, self.queries, self.hints, self.prepared,
                               cutoff=self.cutoff, model_info=self.native.info)

    def test_full_schedule_includes_uncertain_empty_context_and_replays(self):
        with patch.object(p.admission, 'revalidate', wraps=admission.revalidate) as final_check:
            report = self.answer()
        self.assertEqual(final_check.call_count, 1)
        self.assertEqual(report['status'], 'complete')
        self.assertEqual(report['scheduled'], 3)
        self.assertEqual(report['entered'], 3)
        self.assertEqual(report['unexecuted'], 0)
        self.assertTrue(all(r['product']['diagnostic_only'] for r in report['rows']))
        self.assertEqual(report['rows'][1]['product']['disposition']['prediction']['answer_index'], 1)
        self.assertEqual(self.replay()['questions'], 3)
        self.assertFalse((self.source.output / 'products/0001').exists())

    def test_incomplete_or_changed_schedule_fails_before_callback(self):
        self.queries.pop()
        with patch.object(self.native, 'call') as call, self.assertRaisesRegex(ValueError, 'Complete recovered'):
            self.answer(call_model=call)
        self.assertEqual(call.call_count, 0)
        self.assertFalse(self.output.exists())

    def test_every_source_is_preflighted_before_first_callback(self):
        original = admission.capture
        seen = []
        def capture(query, *args, **kwargs):
            seen.append(query['id'])
            return original(query, *args, **kwargs)
        def call(*args):
            self.assertEqual(seen, [q['id'] for q in self.queries])
            return self.native.call(*args)
        with patch.object(p.admission, 'capture', side_effect=capture):
            self.assertEqual(self.answer(call_model=call)['status'], 'complete')

    def test_preflight_failure_leaves_all_answers_unexecuted(self):
        original = admission.capture
        def bad(query, *args, **kwargs):
            if query['id'] == self.queries[-1]['id']:
                raise ValueError('Invented source preflight failure')
            return original(query, *args, **kwargs)
        with patch.object(p.admission, 'capture', side_effect=bad), patch.object(self.native, 'call') as call:
            with self.assertRaisesRegex(ValueError, 'Invented source'):
                self.answer(call_model=call)
        self.assertEqual(call.call_count, 0)
        report = p.native_replay.load(self.output / 'REPORT.json')
        self.assertEqual((report['status'], report['entered'], report['unexecuted']), ('partial', 0, 3))
        self.assertTrue((self.output / 'ANSWER-FAILURE.json').exists())

    def test_interrupted_callback_retains_partial_schedule_without_repeat(self):
        with patch.object(self.native, 'call', side_effect=KeyboardInterrupt('Invented interruption')) as call:
            with self.assertRaises(KeyboardInterrupt):
                self.answer(call_model=call)
            self.assertEqual(call.call_count, 1)
            with self.assertRaises(FileExistsError):
                self.answer(call_model=call)
            self.assertEqual(call.call_count, 1)
        report = p.native_replay.load(self.output / 'REPORT.json')
        self.assertEqual(report['entered'], 1)
        self.assertEqual(report['unexecuted'], 2)
        self.assertEqual(report['rows'][0]['status'], 'interrupted')

    def test_malformed_response_keeps_native_usage_in_full_denominator(self):
        self.native.bad_codec = True
        report = self.answer()
        self.assertEqual(report['scheduled'], 3)
        self.assertTrue(all(r['product']['disposition']['producer_status'] == 'parse_failure' for r in report['rows']))
        self.assertTrue(all(r['product']['call']['summary']['usage']['input_tokens'] == 50 for r in report['rows']))
        self.assertEqual(self.replay()['status'], 'verified')

    def test_final_collection_change_cannot_publish_complete_stage(self):
        with patch.object(p.admission, 'revalidate', side_effect=ValueError('Invented changed collection')):
            with self.assertRaisesRegex(ValueError, 'changed collection'):
                self.answer()
        report = p.native_replay.load(self.output / 'REPORT.json')
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['entered'], 3)
        self.assertEqual(report['unexecuted'], 0)
        with self.assertRaises(ValueError):
            self.replay()

    def test_same_bytes_from_different_model_output_root_are_rejected(self):
        def misplaced(task, query, items, output, deadline):
            return self.native.call(task, query, items, self.source.top / 'other-cell', deadline)
        with self.assertRaisesRegex(ValueError, 'escaped'):
            self.answer(call_model=misplaced)
        report = p.native_replay.load(self.output / 'REPORT.json')
        self.assertEqual((report['status'], report['entered'], report['unexecuted']), ('partial', 1, 2))

    def test_resealed_context_change_is_rejected(self):
        self.answer()
        path = self.output / 'preflight/0001.json'
        value = p.native_replay.load(path)
        value['query_sha256'] = '0' * 64
        path.write_bytes(canonical(value))
        receipt_path = self.output / 'STAGE-RECEIPT.json'
        receipt = p.native_replay.load(receipt_path)
        receipt['files'] = p.schedule.journal_inventory(self.output)
        receipt_path.write_bytes(canonical(receipt))
        with self.assertRaisesRegex(ValueError, 'context replay'):
            self.replay()


class PositiveRecoveryAnswerTests(unittest.TestCase):
    def test_positive_and_uncertain_questions_keep_original_sources_in_native_replay(self):
        from experiments.litqa_recovery import test_admission as source_controls
        source = source_controls.RecoveredAdmissionTests('runTest')
        source.setUp()
        self.addCleanup(source.doCleanups)
        self.addCleanup(source.tearDown)
        native = native_fixtures.ReplayTests('runTest')
        native.setUp()
        self.addCleanup(native.doCleanups)
        output = source.top / 'answers'
        cutoff = datetime.now(timezone.utc) + timedelta(minutes=1)
        report = p.answer(source.f.queries, source.f.hints, source.prepared, output,
                          seconds=180, cutoff=cutoff, model_provenance=native.info['provenance'],
                          call_model=native.call)
        rows = report['rows']
        self.assertEqual([row['product']['disposition']['prediction']['answer_index'] for row in rows], [0, 1, 0])
        self.assertTrue(rows[0]['product']['disposition']['prediction']['evidence_ids'])
        self.assertFalse(rows[1]['product']['disposition']['prediction']['evidence_ids'])
        contexts = [p.native_replay.load(output / 'products' / f'{i:04d}' / 'CONTEXT.json') for i in range(3)]
        self.assertEqual(contexts[0]['coverage']['inherited_uncertain_inputs'], [source.f.dois[1]])
        self.assertEqual(contexts[2]['coverage']['retained_articles'], 2)
        self.assertEqual(p.replay_answers(output, p.primary.proof(output / 'STAGE-RECEIPT.json')['sha256'],
                                         source.f.queries, source.f.hints, source.prepared,
                                         cutoff=cutoff, model_info=native.info)['status'], 'verified')


if __name__ == '__main__':
    unittest.main()
