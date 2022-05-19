from datetime import date
from unittest import TestCase

from bank.orm import Investment
from tests._utils import TODAY, TOMORROW, YESTERDAY, DAY_AFTER_TOMORROW, DAY_BEFORE_YESTERDAY


def create_investment(
        start_date=YESTERDAY,
        end_date=TOMORROW,
        service_units=10_000,
        current_sus=5_000,
        withdrawn_sus=1_000,
        rollover_sus=0
) -> Investment:
    """Create an ``Investment`` instance for testing

    Function defaults are chosen to create an active/unexpired investment.
    See the ``Investment`` class for argument descriptions.
    """

    return Investment(
        start_date=start_date,
        end_date=end_date,
        service_units=service_units,
        current_sus=current_sus,
        withdrawn_sus=withdrawn_sus,
        rollover_sus=rollover_sus
    )


class ServiceUnitsValidation(TestCase):
    """Tests for the validation of the ``service_units`` column"""

    def test_negative_service_units(self) -> None:
        """Test for a ``ValueError`` when the number of service units are negative"""

        with self.assertRaises(ValueError):
            Investment(service_units=-1)

    def test_zero_service_units(self) -> None:
        """Test for a ``ValueError`` when the number of service units are zero"""

        with self.assertRaises(ValueError):
            Investment(service_units=0)

    def test_value_is_assigned(self) -> None:
        """Test the validated value is assigned to the table instance"""

        num_sus = 10
        investment = Investment(service_units=num_sus)
        self.assertEqual(num_sus, investment.service_units)


class InvestmentStatus(TestCase):
    """Tests for the determination of a DB proposal/investment being active"""

    def test_current_date_before_range(self) -> None:
        """Test the record is inactive and unexpired before the record date range"""

        record = create_investment(start_date=TOMORROW, end_date=DAY_AFTER_TOMORROW)
        self.assertFalse(record.is_active)

    def test_current_date_in_range(self) -> None:
        """Test the record is active and unexpired during the record date range"""

        record = create_investment(start_date=YESTERDAY, end_date=TOMORROW)
        self.assertTrue(record.is_active)

    def test_current_date_after_range(self) -> None:
        """Test the record is inactive and expired after the record date range"""

        record = create_investment(start_date=DAY_BEFORE_YESTERDAY, end_date=YESTERDAY)
        self.assertFalse(record.is_active)

    def test_current_date_at_start(self) -> None:
        """Test the record is active and unexpired on the start date"""

        record = create_investment(start_date=TODAY, end_date=TOMORROW)
        self.assertTrue(record.is_active)

    def test_current_date_at_end(self) -> None:
        """Test the record is inactive and expired on the end date"""

        record = create_investment(start_date=YESTERDAY, end_date=TODAY)
        self.assertFalse(record.is_active)


class IsExpiredProperty(TestCase):
    """Tests for the ``is_expired`` property"""

    def test_not_expired_with_sus_and_in_range(self):
        """Test valid investments are not marked"""

        investment = create_investment()
        self.assertFalse(investment.is_expired)

    def test_expired_if_past_end_date(self) -> None:
        """Test an investment is is_expired if it is past its end date"""

        investment = create_investment()
        investment.end_date = date.today()
        self.assertTrue(investment.is_expired)

    def test_expired_if_no_more_service_units(self) -> None:
        """Test an investment is is_expired if it has no more service units"""

        investment = create_investment()
        investment.current_sus = 0
        investment.withdrawn_sus = investment.service_units
        self.assertTrue(investment.is_expired)

    def test_expired_if_exhausted(self) -> None:
        """Test an investment is expired if it has been marked as exhausted"""

        investment = create_investment()
        investment.exhaustion_date = TODAY
        self.assertTrue(investment.is_expired)
