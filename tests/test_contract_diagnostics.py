"""Contract clarity fixes preserve successful decoding and canonical data."""
from dataclasses import MISSING, fields
from datetime import date
import unittest

from asof.contracts import Observation, Snapshot
from asof.serde import ContractError, decode


class ContractDiagnosticsTests(unittest.TestCase):
    def test_mapping_defaults_are_factories_not_misleading_none(self):
        for cls, names in ((Snapshot, ('coverage',)),
                           (Observation, ('source_locator', 'source_metrics', 'missingness'))):
            available = {field.name: field for field in fields(cls)}
            for name in names:
                with self.subTest(contract=cls.__name__, field=name):
                    self.assertIsNot(available[name].default_factory, MISSING)
                    self.assertEqual(available[name].default_factory(), {})

    def test_union_retains_each_branch_diagnostic(self):
        with self.assertRaises(ContractError) as caught:
            decode(date | None, 'bad-date', 'packet.publication_date')
        cause = caught.exception.__cause__
        self.assertIsInstance(cause, ExceptionGroup)
        self.assertEqual(len(cause.exceptions), 2)
        self.assertTrue(any('date' in str(error) for error in cause.exceptions))
        self.assertTrue(any('null' in str(error) for error in cause.exceptions))

    def test_valid_union_and_strict_mapping_null_stay_unchanged(self):
        self.assertEqual(decode(date | None, '2020-01-01'), date(2020, 1, 1))
        self.assertIsNone(decode(date | None, None))
        with self.assertRaises(ContractError):
            decode(dict[str, str], None)


if __name__ == '__main__':
    unittest.main()
