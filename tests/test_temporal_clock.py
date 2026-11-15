"""Information-clock boundaries use UTC and retain calendar precision."""
from datetime import date, datetime, timedelta, timezone
import unittest

from tether_engine.contracts import Availability
from tether_engine.serde import ContractError
from tether_engine.temporal import available_by, calendar_bounds, utc_instant
from tools.science.qualification import validate_feature_chronology


class TemporalClockRegressions(unittest.TestCase):
    def availability(self, known, retrieved):
        return Availability(None, None, None, None, retrieved, 'documented public release', None,
                            known_public_by=known, evidence_ref='fictional-release-proof')

    def test_retrieval_day_is_compared_in_utc(self):
        cutoff = datetime(2023, 1, 3, tzinfo=timezone.utc)
        next_utc_day = datetime(2023, 1, 1, 23, tzinfo=timezone(timedelta(hours=-2)))
        self.assertEqual(self.availability(next_utc_day, date(2023, 1, 1)).exclusion(cutoff),
                         'availability_after_retrieval')

    def test_equivalent_offset_cannot_create_false_retrieval_rejection(self):
        cutoff = datetime(2023, 1, 3, tzinfo=timezone.utc)
        prior_utc_day = datetime(2023, 1, 2, 0, tzinfo=timezone(timedelta(hours=2)))
        self.assertIsNone(self.availability(prior_utc_day, date(2023, 1, 1)).exclusion(cutoff))

    def test_feature_information_available_at_origin_is_eligible(self):
        origin = '2023-01-01T00:00:00Z'
        inputs = [{'sha256': 'a' * 64, 'available_by': origin, 'role': 'agent_evidence'}]
        self.assertEqual(validate_feature_chronology(origin, inputs)['status'], 'feature_chronology_valid')

    def test_exact_equality_is_distinct_from_one_microsecond_later(self):
        origin = datetime(2023, 1, 1, tzinfo=timezone.utc)
        self.assertTrue(available_by(origin, origin))
        self.assertFalse(available_by(origin + timedelta(microseconds=1), origin))
        self.assertTrue(available_by('2023-01-01T02:00:00+02:00', origin))

    def test_date_only_availability_does_not_claim_intraday_precision(self):
        day = date(2023, 1, 1)
        availability = Availability(day, day, day, day, day, 'fictional dated release', None)
        self.assertEqual(availability.exclusion(datetime(2023, 1, 1, 12, tzinfo=timezone.utc)),
                         'available_after_origin')
        self.assertIsNone(availability.exclusion(calendar_bounds(day).latest))

    def test_calendar_bounds_preserve_leap_month_and_year_precision(self):
        month = calendar_bounds('2024-02')
        self.assertEqual(month.precision, 'month')
        self.assertEqual(month.lower, datetime(2024, 2, 1, tzinfo=timezone.utc))
        self.assertEqual(month.latest, datetime(2024, 2, 29, 23, 59, 59, 999999, timezone.utc))
        self.assertFalse(available_by(month.latest, '2024-02-15T12:00:00Z'))
        year = calendar_bounds(2024)
        self.assertEqual(year.precision, 'year')
        self.assertEqual(year.latest.date(), date(2024, 12, 31))
        self.assertEqual(calendar_bounds('9999').latest.year, 9999)

    def test_ambiguous_or_truncated_instants_fail_at_boundary(self):
        for value in ('2024-01-01', '2024-W01-1T00:00:00Z', '20240101T000000Z',
                      '2024-01-01T00:00:00', '2024-01-01T00:00:00.1234567Z',
                      True, datetime(2024, 1, 1)):
            with self.subTest(value=value), self.assertRaisesRegex(ContractError, 'explicit timezone-aware ISO instant'):
                utc_instant(value)
        for value in ('2024-02-30', '2024-00', '2024-01-00', True, None, '2024-W01'):
            with self.subTest(calendar=value), self.assertRaisesRegex(ContractError, '[Cc]alendar time'):
                calendar_bounds(value)


if __name__ == '__main__':
    unittest.main()
