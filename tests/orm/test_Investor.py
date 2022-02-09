"""Tests for the ``Investor`` class"""

from datetime import date, timedelta
from unittest import TestCase

from bank.orm import Investor, Session
from tests.orm import _utils


class ServiceUnitsValidation(TestCase, _utils.ServiceUnitsValidation):
    """Tests for the validation of the service units"""

    db_table_class = Investor
    columns_to_test = ('service_units',)


class ToArchiveObject(TestCase):
    """Test the conversion of an investor to an archive object"""

    def setUp(self) -> None:
        """Create a ``Investor`` instance for testing"""

        self.investment = Investor(
            account_name='username',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            service_units=10_000,
            current_sus=5_000,
            withdrawn_sus=1_000,
            rollover_sus=0
        )

        self.archive_obj = self.investment.to_archive_object()

    def test_column_values_match_original_object(self) -> None:
        """Test the attributes of the returned object match the original investment"""

        col_names = ('id', 'account_name', 'start_date', 'end_date', 'service_units', 'current_sus')
        for c in col_names:
            self.assertEqual(getattr(self.investment, c), getattr(self.archive_obj, c))

    def test_default_end_date_is_today(self) -> None:
        """Test that the default value for the ``end_date`` column is the current date"""

        self.assertEqual(self.archive_obj.exhaustion_date, date.today())

    def test_returned_obj_matches_target_table_schema(self) -> None:
        """Check no errors are raised when adding the archive object to the archive table"""

        with Session() as session:
            session.add(self.archive_obj)
            session.flush()


class Expired(TestCase):
    """Tests for the ``expired`` property"""

    def setUp(self) -> None:
        """Create a ``Investor`` instance for testing"""

        self.investment = Investor(
            account_name='username',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            service_units=10_000,
            current_sus=5_000,
            withdrawn_sus=1_000,
            rollover_sus=0
        )

    def test_expired_if_past_end_date(self) -> None:
        """Test the investment is expired if it is past its end date"""

        self.assertFalse(self.investment.expired)

        self.investment.end_date = date.today()
        self.assertTrue(self.investment.expired)

    def test_expired_if_no_more_service_units(self) -> None:
        """Test the investment is expired if it has no more service units"""

        self.assertFalse(self.investment.expired)

        self.investment.current_sus = 0
        self.investment.withdrawn_sus = self.investment.service_units
        self.assertTrue(self.investment.expired)
