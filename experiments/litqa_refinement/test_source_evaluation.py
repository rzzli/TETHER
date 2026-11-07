"""Invented independent source/context controls; never accesses released keys."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch

from tether_engine.serde import encode, canonical, fingerprint
from experiments.labbench import tether_adapter
from . import admission, contracts, selection
from . import test_admission as fixtures
from . import source_evaluation as s


class SourceEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.AdmissionTests('runTest')
        self.f.setUp(); self.addCleanup(self.f.doCleanups)
        self.catalog = s.native.proof(Path(tether_adapter.__file__))
        self.code = s.native.proof(Path(selection.__file__))

    def read(self, context, *, original=None, new='default', cutoff=None, catalog=None):
        return s.reconstruct_context(context.report if hasattr(context, 'report') else context, self.f.query,
            self.f.prior, self.f.critique, original_descriptor=original or self.f.original,
            refinement_descriptor=self.f.new if new == 'default' else new, cutoff=cutoff or self.f.cutoff,
            catalog_proof=catalog or self.catalog, selection_proof=self.code)

    def test_complete_original_new_raw_ancestry_and_context_reconstructed(self):
        context = self.f.capture()
        got = self.read(context)
        self.assertEqual(canonical(got['sources']), canonical(context.sources))
        self.assertTrue(got['source_lineage_checked'])
        self.assertFalse(got['scientific_support_verified'])
        self.assertEqual(len(got['context']['merge']['sources']), 2)
        self.assertTrue(got['source_context_changed'])
        self.assertEqual(got['original_retained_dois'], got['original']['retained_dois'])
        self.assertEqual(got['original_pool_dois'], got['original']['pool_dois'])
        # This fixture reports no DOI; raw passage availability must not invent one.
        self.assertEqual(got['original_selected_dois'], [])
        self.assertTrue(all(p['parents'] == [] for p in got['context']['source_proofs']))

    def test_duplicate_alias_and_conflicting_version_both_reconstructed(self):
        for name, text, expected in (('same', None, 1), ('different', 'The fictional color is amber.', 0)):
            kwargs = {} if text is None else dict(text=text)
            new = self.f.make_refinement(name, ('PMC1',), **kwargs)
            context = self.f.capture(new=new)
            got = self.read(context, new=new)
            self.assertEqual(len(got['context']['merge']['sources']), expected)
            if expected:
                self.assertEqual(len(got['context']['bindings'][0]['receipt_aliases']), 2)
            else:
                self.assertEqual(len(got['context']['merge']['exclusions']), 1)
                self.assertEqual(got['sources'], [])

    def test_unavailable_critic_keeps_explicit_missing_refinement_without_receipt(self):
        self.f.critique = contracts.critique(self.f.query, self.f.prior, self.f.old_sources, None,
            native_status='capacity', native_call_sha256=None)
        self.f.control = fingerprint(dict(query=self.f.query, candidate=self.f.prior, critique=self.f.critique))
        context = self.f.capture(new=None, unavailable_reason='refinement_query_unavailable')
        got = self.read(context, new=None)
        self.assertIsNone(got['refinement'])
        self.assertIsNone(got['context']['coverage']['refinement'])
        self.assertEqual(got['projected_refinement']['cause'], 'critic_capacity')
        self.assertTrue(got['sources'])

    def test_valid_critic_collection_cannot_be_silently_omitted(self):
        context = self.f.capture(new=None, unavailable_reason='refinement_query_unavailable')
        with self.assertRaisesRegex(ValueError, 'requires the one'): self.read(context, new=None)

    def test_six_articles_preserve_every_original_span_and_locator(self):
        old = self.f.make_original('six-old', ('PMC10', 'PMC11', 'PMC12'))
        raw = s.original.reconstruct(old['root'], old['receipt_sha256'], encode(old['plan']))
        self.f.old_sources = s.original.selection(raw['manifest']['pool']['pool'])
        self.f.prior, self.f.critique = fixtures.fixtures.critic_for(self.f.query, self.f.old_sources)
        self.f.control = fingerprint(dict(query=self.f.query, candidate=self.f.prior, critique=self.f.critique))
        new = self.f.make_refinement('six-new', ('PMC13', 'PMC14', 'PMC15'))
        context = self.f.capture(original=old, new=new)
        got = self.read(context, original=old, new=new)
        self.assertEqual(len(got['context']['merge']['sources']), 6)
        self.assertTrue(all('original_locator' in b for b in got['context']['bindings']))
        self.assertLessEqual(len(got['sources']), 8)

    def test_missing_parent_future_clock_and_renamed_evaluator_role_fail(self):
        context = self.f.capture()
        with self.assertRaisesRegex(ValueError, 'availability cutoff'):
            self.read(context, cutoff='2026-11-06T00:00:00+00:00')
        raw = Path(tether_adapter.__file__).read_text(encoding='utf8')
        fake = self.f.root/'renamed.py'
        fake.write_text(raw.replace('"agent_evidence"', '"evaluation_only"'), encoding='utf8')
        with self.assertRaisesRegex(ValueError, 'Evidence-only'):
            self.read(context, catalog=s.native.proof(fake))
        original = Path(self.f.original['root']); first = next((original/'responses').glob('*.body'))
        first.write_bytes(first.read_bytes()+b' ')
        with self.assertRaisesRegex(ValueError, 'bytes changed'): self.read(context)

    def test_control_as_evidence_wrong_original_locator_and_context_mutation_rejected(self):
        context = self.f.capture()
        for kind in ('role', 'locator', 'parent', 'missing'):
            report = encode(context.report)
            if kind == 'role': report['control_is_scientific_evidence'] = True
            if kind == 'locator': report['bindings'][0]['original_locator']['paragraph_index'] += 1
            if kind == 'parent': report['source_proofs'][0]['parents'] = ['generated-critic']
            if kind == 'missing': report['source_proofs'].pop()
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, 'context reconstruction'): self.read(report)

    def test_disposition_matches_current_raw_admission_and_removal_mechanics(self):
        context = self.f.capture(); pair = self.f.requests(context)
        for task, pred in (('repair', dict(answer_index=0, evidence_ids=[context.sources[0]['source_id']])),
                           ('removal', dict(answer_index=0, evidence_ids=[])),
                           ('removal', dict(answer_index=2, evidence_ids=[]))):
            member = pair[task]
            got = s.disposition(self.f.query, dict(summary=dict(status='completed', task=task, decoded=pred,
                request_sha256=fingerprint(member['request']))), encode(context.report))
            actual = admission.check(context, pred, member['request'], task=task,
                expected_control_sha256=self.f.control, payload=member['payload'])
            self.assertEqual(canonical(got['decision']), canonical(actual))

    def test_receipt_decoding_must_use_exact_externally_hashed_bytes(self):
        root = Path(self.f.original['root']); receipt_path = root/'RECEIPT.json'
        real_load = s.n.load
        def transient(path):
            value = real_load(path)
            if Path(path) == receipt_path: value['status'] = 'invented_unanchored_status'
            return value
        with patch.object(s.n, 'load', side_effect=transient):
            receipt, _ = s.inventory(root, self.f.original['receipt_sha256'])
        self.assertEqual(receipt['status'], 'complete')


if __name__ == '__main__':
    unittest.main()
