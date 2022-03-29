"""Tests for the ``Investor`` class"""

from datetime import date, timedelta
from unittest import TestCase

from bank.orm import Investment
from tests.orm import _utils


class ServiceUnitsValidation(TestCase, _utils.ServiceUnitsValidation):
    """Tests for the validation of the service units"""

    db_table_class = Investment
    columns_to_test = ('service_units',)


class Expired(TestCase):
    """Tests for the ``is_expired`` property"""

    def setUp(self) -> None:
        """Create a ``Investor`` instance for testing"""

        self.investment = Investment(
            account_name='username',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            service_units=10_000,
            current_sus=5_000,
            withdrawn_sus=1_000,
            rollover_sus=0
        )

    def test_expired_if_past_end_date(self) -> None:
        """Test the investment is is_expired if it is past its end date"""

        self.assertFalse(self.investment.is_expired)

        self.investment.end_date = date.today()
        self.assertTrue(self.investment.is_expired)

    def test_expired_if_no_more_service_units(self) -> None:
        """Test the investment is is_expired if it has no more service units"""

        self.assertFalse(self.investment.is_expired)

        self.investment.current_sus = 0
        self.investment.withdrawn_sus = self.investment.service_units
        self.assertTrue(self.investment.is_expired)
