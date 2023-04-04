"""Tests for the `Investment`` class."""

from datetime import date
import time_machine
from unittest import TestCase

from sqlalchemy import select

from bank import settings
from bank.orm import Account, DBConnection, Investment
from tests._utils import account_investments_query, add_investment_to_test_account, DAY_AFTER_TOMORROW, EmptyAccountSetup, TODAY

# Start and End date values to use with time_machine
start = TODAY
end = DAY_AFTER_TOMORROW


def create_investment(
        start_date=TODAY-1,
        end_date=TODAY+1,
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

        record = create_investment(start_date=TODAY+1, end_date=DAY_AFTER_TOMORROW)
        self.assertFalse(record.is_active)

    def test_current_date_in_range(self) -> None:
        """Test the record is active and unexpired during the record date range"""

        record = create_investment(start_date=TODAY-1, end_date=TODAY+1)
        self.assertTrue(record.is_active)

    def test_current_date_after_range(self) -> None:
        """Test the record is inactive and expired after the record date range"""

        record = create_investment(start_date=TODAY-2, end_date=TODAY-1)
        self.assertFalse(record.is_active)

    def test_current_date_at_start(self) -> None:
        """Test the record is active and unexpired on the start date"""

        record = create_investment(start_date=TODAY, end_date=TODAY+1)
        self.assertTrue(record.is_active)

    def test_current_date_at_end(self) -> None:
        """Test the record is inactive and expired on the end date"""

        record = create_investment(start_date=TODAY-1, end_date=TODAY)
        self.assertFalse(record.is_active)


class ExpiredProperty(EmptyAccountSetup, TestCase):
    """Tests for the ``is_expired`` property"""

    def test_is_expired_no_investment_sus(self) -> None:
        """ Test ``is_expired`` for various date ranges on an investment without any service units remaining"""

        # Create the Investment and add it to the DB
        investment = create_investment(start_date=start,end_date=end)
        investment.current_sus = 0
        add_investment_to_test_account(investment)

        with DBConnection.session() as session:
            investment = session.execute(account_investments_query).scalars().first()

            self.assertTrue(investment.is_expired)
            self.assertIn(investment.id, session.execute(select(Investment.id)
                                                         .join(Account)
                                                         .where(Account.name == settings.test_accounts[0])
                                                         .where(Investment.is_expired)).scalars().all())

    def test_is_expired_has_investment_sus(self) -> None:
        """ Test ``is_expired`` for various date ranges on an investment with service units remaining"""

        investment = create_investment(start_date=start, end_date=end)
        investment.current_sus = investment.service_units
        add_investment_to_test_account(investment)

        #with DBConnection.session() as session:
            #investment =  session.execute(account_invest)

    def test_not_expired_with_sus_and_in_range(self) -> None:
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


class ActiveProperty(EmptyAccountSetup, TestCase):
    """Test the boolean ``is_active`` hybrid property and it's SQL expression form"""

    def test_is_expired_no_investment_sus(self) -> None:
        """ Test ``is_expired`` for various date ranges on an investment without any service units remaining"""

        # Create the Investment and add it to the DB
        investment = create_investment(start_date=start,end_date=end)
        investment.current_sus = investment.service_units
        add_investment_to_test_account(investment)
