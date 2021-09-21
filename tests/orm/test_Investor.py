"""Tests for the ``Investor`` class"""

from datetime import date, timedelta
from unittest import TestCase

from bank.orm import Investor


class ToArchiveObject(TestCase):
    """Test the conversion of a proposal to an archive object"""

    def setUp(self) -> None:
        """Create a proposal instance for testing"""

        self.investment = Investor(
            account_name='username',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            service_units=10_000,
            current_sus=5_000,
            withdrawn_sus=1_000,
            rollover_sus=0
        )

    def test_column_values_match_original_object(self) -> None:
        """Test the attributes of the returned object match the original investment"""

        archive_obj = self.investment.to_archive_object()
        self.assertEqual(self.investment.id, archive_obj.id)
        self.assertEqual(self.investment.account_name, archive_obj.account_name)
        self.assertEqual(self.investment.start_date, archive_obj.start_date)
        self.assertEqual(self.investment.end_date, archive_obj.end_date)
        self.assertEqual(self.investment.service_units, archive_obj.service_units)
        self.assertEqual(self.investment.current_sus, archive_obj.current_sus)

    def test_default_end_date_is_today(self) -> None:
        """Test that the default value for the ``end_date`` column is the current date"""

        archive_obj = self.investment.to_archive_object()
        self.assertEqual(archive_obj.exhaustion_date, date.today())
