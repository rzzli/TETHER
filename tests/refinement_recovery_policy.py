"""Current admission must reject the frozen SC04 transform before answer dispatch."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from tether_engine.serde import ContractError, sha256_file
from experiments.litqa_comparison import acquisition, admission, qualification_fixtures


class RecoveryPolicyBoundaryTests(unittest.TestCase):
    def test_frozen_producer_rejected_before_answer_request(self):
        query = qualification_fixtures.queries()[0]
        plan = acquisition.plan({key: query[key] for key in ('id', 'question')}, 'lexical')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory).resolve() / 'invented-acquisition'
            with patch.object(acquisition.legacy, 'fetch_http', side_effect=qualification_fixtures.fetch):
                acquisition.acquire(plan, output, deadline=time.monotonic() + 30)
            with patch.object(admission.transport, 'make_answer_request') as answer:
                with self.assertRaisesRegex(ContractError, 'Computed lineage requires a registered derivation'):
                    admission.capture(query, output, sha256_file(output/'RECEIPT.json'), plan,
                                      datetime.now(timezone.utc), {})
            answer.assert_not_called()

    def test_partition_preserves_every_method_and_exact_legacy_group(self):
        from tests import test_refinement_recovery as selection
        whole = list(selection._flatten(selection._recovery_suite(unittest.TestLoader())))
        current, legacy = selection._partition(unittest.TestSuite(whole))
        self.assertEqual(len(legacy), 16)
        self.assertCountEqual([test.id() for test in whole],
                              [test.id() for test in (*current, *legacy)])
        self.assertTrue(set(test.id() for test in current).isdisjoint(test.id() for test in legacy))
        self.assertEqual(selection.legacy_test_inventory(), sorted(test.id() for test in legacy))
        with self.assertRaisesRegex(AssertionError, 'inventory changed'):
            selection._partition(unittest.TestSuite(current + legacy[:-1]))

    def test_validation_report_does_not_promote_legacy_selection_to_a_pass(self):
        from tools.validate import legacy_compatibility_scope
        scope = legacy_compatibility_scope()
        self.assertEqual(scope['status'], 'not_executed_by_current_policy_gate')
        self.assertEqual(scope['tests'], 16)
        self.assertEqual(len(scope['test_ids']), 16)
        self.assertEqual(scope['required_engine_version'], '0.4.0')
        self.assertFalse(scope['current_policy_qualified'])
