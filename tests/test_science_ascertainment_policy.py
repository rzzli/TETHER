import unittest
from tether_engine.serde import ContractError
from tools.science.ascertainment_policy import publication_bounds,version_eligibility


class AscertainmentPolicyTests(unittest.TestCase):
    def disposition(self,value,**kwargs):
        return version_eligibility(last_update_posted_date=value,
            cutoff_at='2026-04-01T00:00:00Z',**kwargs)

    def test_civil_offset_envelope_is_explicit_and_conservative(self):
        bounds=publication_bounds('2026-03-30')
        self.assertEqual(bounds['lower'],'2026-03-29T10:00:00+00:00')
        self.assertEqual(bounds['upper_exclusive'],'2026-03-31T12:00:00+00:00')
        result=self.disposition('2026-03-30')
        self.assertEqual(result['status'],'eligible_reconstructed_date_bound')
        self.assertFalse(result['strict_timestamp_qualified'])
        self.assertFalse(result['original_version_bytes_qualified'])
        self.assertIsNone(result['clinical_label'])

    def test_boundary_dates_do_not_extend_ascertainment_cutoff(self):
        for day in ('2026-03-31','2026-04-01'):
            self.assertEqual(self.disposition(day)['status'],'held_boundary_uncertain')
        self.assertEqual(self.disposition('2026-04-02')['status'],'held_after_cutoff')

    def test_initial_registration_does_not_backdate_latest_version(self):
        result=self.disposition('2026-04-01',first_posted_date='2010-01-01')
        self.assertEqual(result['status'],'held_boundary_uncertain')
        self.assertEqual(self.disposition(None,first_posted_date='2010-01-01')['status'],
                         'held_missing_version_date')

    def test_partial_missing_dates_are_held_and_bad_dates_fail(self):
        for value in (None,'2026','2026-03'):
            self.assertEqual(self.disposition(value)['status'],'held_missing_version_date')
        for value in ('2026-02-31','2026-04-01T00:00Z','not-a-date',42):
            with self.assertRaises(ContractError):self.disposition(value)
        with self.assertRaises(ContractError):self.disposition('2026-03-30',first_posted_date='2026-04-01')

    def test_original_origin_maximum_is_eligible_without_reselection(self):
        result=version_eligibility(last_update_posted_date='2024-12-27',
            cutoff_at='2025-01-01T00:00:00Z')
        self.assertEqual(result['status'],'eligible_reconstructed_date_bound')

    def test_naive_non_utc_and_invalid_cutoffs_fail(self):
        for cutoff in ('2026-04-01','2026-04-01T01:00:00+01:00','bad'):
            with self.assertRaises(ContractError):
                version_eligibility(last_update_posted_date='2026-03-30',cutoff_at=cutoff)
