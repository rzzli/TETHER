"""Independent synthetic regression expectations for the contextual contract.

These tests independently check the reported contract boundaries. No biological
claim, native run, ignored input, network request or model call is involved.
"""
import unittest

from tether_engine.serde import ContractError
from tests import test_science_t6_contextual_audit as fixtures
from tools.science.t6_contextual_audit import validate_inventory


class ContextualPeerTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ContextualContractTests(methodName='runTest')
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def numeric_claim(self, source='r1'):
        f = self.f
        claim = f.inventory['claims'][0]
        numeric = next(n for n in f.surface['nodes']
                       if n.get('pointer') == '/textMiningSentences/2/text'
                       and n['source_unit_id'] == source)
        claim['unit_kind'] = 'estimate_bundle'
        claim['context_fragments'] = [f.fragment(numeric)]
        claim['proposition'].update(subject='X', predicate='associated with', object='Y',
                                    orientation=dict(exposure='X', outcome='Y'))
        claim['numeric_bundle'] = dict(estimate=f.fragment(numeric, '-0.02'),
            interval=f.fragment(numeric, '[-0.03,-0.01]'),
            p_value=f.fragment(numeric, '0.01', last=True), scale=None,
            reason='Invented numerical fixture.')
        return claim

    def test_record_bundle_cannot_import_another_records_numbers(self):
        self.numeric_claim()
        validate_inventory(self.f.inventory, self.f.surface)
        self.numeric_claim(source='r2')
        # The focus and explicit record context remain r1. Every number and its
        # surrounding methodological context come only from r2.
        with self.assertRaises(ContractError):
            validate_inventory(self.f.inventory, self.f.surface)

    def test_substring_inside_signed_estimate_is_not_reported_estimate(self):
        claim = self.numeric_claim()
        validate_inventory(self.f.inventory, self.f.surface)
        # The source's -0.02 is not a report of +0.02. Even a lexically exact
        # substring must retain the complete signed numerical token.
        estimate = claim['numeric_bundle']['estimate']
        estimate['span']['start'] += 1
        estimate['text'] = '0.02'
        with self.assertRaises(ContractError):
            validate_inventory(self.f.inventory, self.f.surface)

    def test_uncertainty_axis_remains_visible_in_descriptive_report(self):
        self.f.review['claims'][0]['uncertainty'] = 'high'
        result = self.f.assess()
        axes = result['strata'][0]['axes']
        self.assertEqual(axes.get('uncertainty'), {'high': 1})


if __name__ == '__main__':
    unittest.main()
