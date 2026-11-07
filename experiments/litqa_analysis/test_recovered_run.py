"""Invented recovered runs; no evaluator keys, live network, models or scores."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import unittest
from unittest.mock import patch

from tether_engine.serde import encode
from experiments.labbench import tether_adapter
from experiments.litqa_comparison import codecs
from experiments.litqa_comparison.tests import test_replay as native_fixtures
from experiments.litqa_recovery import admission, collection as producer_collection, pipeline, plan
from experiments.litqa_recovery import test_admission as source_fixtures
from experiments.litqa_analysis import recovered_run as r


class RecoveredRunTests(unittest.TestCase):
    def setUp(self):
        self.source = source_fixtures.RecoveredAdmissionTests('runTest')
        self.source.setUp(); self.addCleanup(self.source.doCleanups)
        self.native = native_fixtures.ReplayTests('runTest')
        self.native.setUp(); self.addCleanup(self.native.doCleanups)
        self.output = self.source.top/'answers'
        self.cutoff = (datetime.now(timezone.utc)+timedelta(minutes=1)).isoformat()
        self.args = dict(common_root=self.source.top, cutoff=self.cutoff,
            model_provenance=encode(self.native.info['provenance']), alias=self.native.alias,
            owner_pid=12345, configuration=encode(codecs.CONFIG),
            code_proof=r.envelopes.proof(Path(codecs.__file__)),
            catalog_proof=r.envelopes.proof(Path(tether_adapter.__file__)),
            expected_endpoint='http://127.0.0.1:'+str(self.native.info['spec']['port']))

    def produce(self):
        return pipeline.answer(self.source.f.queries, self.source.f.hints, self.source.prepared, self.output,
            seconds=180, cutoff=self.cutoff, model_provenance=self.native.info['provenance'], call_model=self.native.call)

    def check(self, **changes):
        args = dict(self.args, **changes)
        return r.reconstruct(self.source.output, self.source.receipt_sha, self.output,
            r.envelopes.proof(self.output/'STAGE-RECEIPT.json')['sha256'], **args)

    def reseal_stage(self):
        proof = r.envelopes.inventory(self.output, omit=('STAGE-RECEIPT.json',))
        receipt = dict(status='complete', files={k:{f:p[f] for f in ('bytes','sha256')} for k,p in proof.items()})
        (self.output/'STAGE-RECEIPT.json').write_bytes(r.canonical(receipt))

    @staticmethod
    def rechain(path, events):
        previous = None
        for event in events:
            event.pop('sha256'); event['previous_sha256'] = previous
            event['sha256'] = r.digest(r.canonical(event)); previous = event['sha256']
        path.write_bytes(b''.join(r.canonical(e)+b'\n' for e in events))

    def test_all_sources_answers_and_uncertainty_reconstruct_without_producer_calls(self):
        self.produce()
        with patch.object(producer_collection, 'replay', side_effect=AssertionError('Maintained replay forbidden')), \
             patch.object(admission, 'capture', side_effect=AssertionError('Maintained admission forbidden')), \
             patch.object(plan, 'inspect_parent', side_effect=AssertionError('Maintained planner forbidden')), \
             patch.object(pipeline, 'replay_answers', side_effect=AssertionError('Maintained answer replay forbidden')):
            result = self.check()
        self.assertEqual(result['status'], 'independently_reconstructed')
        self.assertEqual([q['id'] for q in result['queries']], [q['id'] for q in self.source.f.queries])
        self.assertEqual([p['prediction']['answer_index'] for p in result['records']['supplied']], [0,1,0])
        self.assertEqual(result['resources']['answer']['model']['generation_calls'], 3)
        self.assertEqual(result['resources']['collection']['accounting']['total']['http_attempts'], 5)
        self.assertEqual(result['resources']['collection']['accounting']['historical']['unknown_transfer_upper_bytes'], 1048576)
        uncertain = result['diagnostic_resolutions'][1]
        self.assertIsNone(uncertain['coverage']['article_retained'])
        self.assertEqual(result['source_cases']['supplied'][1]['logical_http_usage']['requests'], 1)
        self.assertFalse(result['scientific_correctness_scored'])
        self.assertFalse(result['supervised_root_verified'])

    def test_uncertain_raw_journal_tampering_is_not_hidden_by_answer_receipt(self):
        self.produce()
        path = Path(self.source.prepared.manifest['records'][1]['parent_proofs']['journal']['path'])
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaises(ValueError): self.check()

    def test_raw_original_article_tampering_rejected(self):
        self.produce()
        path = self.source.original_source/'responses/001.body'
        path.write_bytes(path.read_bytes().replace(b'cobalt', b'copper'))
        with self.assertRaises(ValueError): self.check()

    def test_resealed_context_cannot_promote_unknown_to_absence(self):
        self.produce()
        for path in (self.output/'preflight/0001.json', self.output/'products/0001/CONTEXT.json'):
            value = r.load(path)
            value['coverage']['sources'][0]['coverage']['article_retained'] = False
            path.write_bytes(r.canonical(value))
        self.reseal_stage()
        with self.assertRaisesRegex(ValueError, 'context differs'): self.check()

    def test_resealed_source_proof_omission_is_rejected(self):
        self.produce()
        for path in (self.output/'preflight/0000.json', self.output/'products/0000/CONTEXT.json'):
            value = r.load(path); value['source_proofs'].pop()
            path.write_bytes(r.canonical(value))
        self.reseal_stage()
        with self.assertRaisesRegex(ValueError, 'context differs'): self.check()

    def test_resealed_native_usage_tampering_rejected(self):
        self.produce()
        path = self.output/'products/0000/SUMMARY.json'
        value = r.load(path); value['usage']['input_tokens'] = 49; path.write_bytes(r.canonical(value))
        self.reseal_stage()
        with self.assertRaisesRegex(ValueError, 'summary'): self.check()

    def test_wrong_endpoint_or_future_cutoff_rejected(self):
        self.produce()
        with self.assertRaisesRegex(ValueError, 'endpoint'): self.check(expected_endpoint='http://127.0.0.1:2')
        with self.assertRaisesRegex(ValueError, 'availability'): self.check(cutoff='2020-01-01T00:00:00+00:00')

    def test_codec_failure_is_retained_in_all_question_denominators(self):
        self.native.bad_codec = True
        self.produce(); result = self.check()
        self.assertEqual(len(result['records']['supplied']), 3)
        self.assertTrue(all(x['producer_status']=='parse_failure' for x in result['records']['supplied']))
        self.assertEqual(result['resources']['answer']['model']['measured_output_tokens'], 36)

    def test_extra_resealed_answer_product_is_rejected(self):
        self.produce(); (self.output/'undeclared.json').write_text('{}')
        self.reseal_stage()
        with self.assertRaisesRegex(ValueError, 'Unexpected recovered answer artifact'): self.check()

    def test_changed_query_choices_are_not_accepted_from_context_alone(self):
        self.produce()
        path = self.output/'products/0000/INPUT.json'
        value = r.load(path); value['query']['choices'][0] = '(A) Changed answer option'
        path.write_bytes(r.canonical(value)); self.reseal_stage()
        with self.assertRaisesRegex(ValueError, 'task identity'): self.check()

    def test_resealed_uncertain_collection_record_cannot_become_measured_absence(self):
        root = self.source.output; path = root/'records/0001.json'; record = r.load(path)
        record['coverage']['article_retained'] = False; record['accounting']['measured_response_bytes'] = 0
        path.write_bytes(r.canonical(record))
        manifest = r.load(root/'MANIFEST.json'); manifest['records'][1] = record
        (root/'MANIFEST.json').write_bytes(r.canonical(manifest))
        complete = r.load(root/'COMPLETE.json'); complete['manifest'] = r.envelopes.proof(root/'MANIFEST.json')
        (root/'COMPLETE.json').write_bytes(r.canonical(complete))
        events = r.journal(root/'journal.jsonl')
        for event in events:
            if event['event'] == 'slot_uncertainty_retained': event['details']['record'] = r.envelopes.proof(path)
        events[-1]['details']['complete'] = r.envelopes.proof(root/'COMPLETE.json')
        self.rechain(root/'journal.jsonl', events)
        receipt = r.load(root/'RECEIPT.json'); receipt['files'] = r.envelopes.inventory(root, omit=('RECEIPT.json',))
        (root/'RECEIPT.json').write_bytes(r.canonical(receipt))
        with self.assertRaisesRegex(ValueError, 'source row/journal'):
            r.reconstruct_collection(root, r.digest((root/'RECEIPT.json').read_bytes()), common_root=self.source.top)

    def test_resealed_admission_decision_is_independently_recomputed(self):
        self.produce(); slot = self.output/'slots/0000.json'; value = r.load(slot)
        value['product']['decision']['accepted'] = False
        slot.write_bytes(r.canonical(value)); report = r.load(self.output/'REPORT.json'); report['rows'][0] = value
        (self.output/'REPORT.json').write_bytes(r.canonical(report)); events = r.journal(self.output/'journal.jsonl')
        events[3]['details']['slot_sha256'] = r.digest(slot.read_bytes())
        events[-1]['details']['report_sha256'] = r.digest((self.output/'REPORT.json').read_bytes())
        self.rechain(self.output/'journal.jsonl', events); self.reseal_stage()
        with self.assertRaisesRegex(ValueError, 'cross-stage product'): self.check()

    def test_empty_hidden_original_attempt_directory_is_not_untouched(self):
        (self.source.f.phase/'products/0002').mkdir()
        with self.assertRaisesRegex(ValueError, 'Unexplained original'):
            r.reconstruct_collection(self.source.output, self.source.receipt_sha, common_root=self.source.top)

    def test_parent_membership_change_during_native_reconstruction_is_rejected(self):
        self.produce(); original = r.native_records.reconstruct
        for directory in (False,True):
            changed=[]; path=self.source.f.root/('late-attempt' if directory else 'late-response.json')
            def mutate_after_sources(*args, **kwargs):
                result = original(*args, **kwargs)
                if not changed:
                    if directory: path.mkdir()
                    else: path.write_text('{}')
                    changed.append(True)
                return result
            try:
                with self.subTest(directory=directory), patch.object(r.native_records,'reconstruct',side_effect=mutate_after_sources):
                    with self.assertRaisesRegex(ValueError,'inventory changed'): self.check()
            finally:
                if path.exists():
                    if directory: path.rmdir()
                    else: path.unlink()


class RecoveryPathTests(unittest.TestCase):
    def test_network_and_alias_roots_reject_before_filesystem_access(self):
        for path in (r'\\server\share\data',r'D:\data\..\source',r'D:\data.\source','relative/path'):
            with self.subTest(path=path), patch.object(r,'_safe_path',side_effect=AssertionError('No filesystem touch')):
                with self.assertRaises(ValueError): r.safe_path(path)


if __name__ == '__main__': unittest.main()
