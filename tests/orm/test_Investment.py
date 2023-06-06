"""Tests for the `Investment`` class."""

from datetime import date, timedelta
import time_machine
from unittest import TestCase

from sqlalchemy import select

from bank import settings
from bank.orm import Account, DBConnection, Investment
from tests._utils import account_investment_ids_query, account_investments_query, add_investment_to_test_account, DAY_AFTER_TOMORROW, EmptyAccountSetup, TODAY

# Start and End date values to use with time_machine
start = TODAY
end = DAY_AFTER_TOMORROW


def create_investment(
        start_date=TODAY - timedelta(days=1),
        end_date=TODAY + timedelta(days=1),
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


class EndDateValidation(TestCase):
    """Test the validation of the ``end_date``` column"""

    def test_error_before_start_date(self) -> None:
        """Test for a ``ValueError`` when the end date is before the start date"""

        today = date.today()
        yesterday = today - timedelta(days=1)
        with self.assertRaisesRegex(ValueError, 'Value for .* column must come after the investment start date'):
            Investment(start_date=today, end_date=yesterday)

    def test_error_on_start_date(self) -> None:
        """Test for a ``ValueError`` when the end date equals the start date"""

        with self.assertRaisesRegex(ValueError, 'Value for .* column must come after the investment start date'):
            Investment(start_date=date.today(), end_date=date.today())

    def test_value_is_assigned(self) -> None:
        """Test the validated value is assigned to the table instance"""

        today = date.today()
        tomorrow = today + timedelta(days=1)
        investment = Investment(start_date=today, end_date=tomorrow)
        self.assertEqual(tomorrow, investment.end_date)


class ExpiredProperty(EmptyAccountSetup, TestCase):
    """Tests for the ``is_expired`` property, and it's SQL expression form"""

    def test_is_expired_no_investment_sus(self) -> None:
        """ Test ``is_expired`` for various date ranges on an investment without any service units remaining

        On start date --> expired
        Before start date --> not expired
        After start date --> expired
        On end date --> expired
        After end date --> expired

        """

        # Create the Investment and add it to the DB
        investment = Investment(start_date=start, end_date=end, current_sus=0, service_units=100, withdrawn_sus=100)
        add_investment_to_test_account(investment)

        # Test is_expired on various dates
        with DBConnection.session() as session:

            investment = session.execute(account_investments_query).scalars().first()

            # On start date -> expired
            self.assertTrue(investment.is_expired)
            self.assertIn(investment.id, session.execute(
                account_investment_ids_query.where(Investment.is_expired)
            ).scalars().all())

            # Before start date -> not expired
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(investment.is_expired)
                self.assertNotIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_expired)
                ).scalars().all())

            # After start date -> expired
            with time_machine.travel(start + timedelta(1)):
                self.assertTrue(investment.is_expired)
                self.assertIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_expired)
                ).scalars().all())

            # On End date -> expired
            with time_machine.travel(end):
                self.assertTrue(investment.is_expired)
                self.assertIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_expired)
                ).scalars().all())

            # After End date -> expired
            with time_machine.travel(end + timedelta(1)):
                self.assertTrue(investment.is_expired)
                self.assertIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_expired)
                ).scalars().all())

    def test_is_expired_has_investment_sus(self) -> None:
        """ Test ``is_expired`` for various date ranges on an investment with service units remaining

        On start date --> not expired
        Before start date --> not expired
        After start date --> not expired
        On end date --> expired
        After end date --> expired

        """

        # Create the Investment and add it to the DB
        investment = Investment(start_date=start, end_date=end, current_sus=100, service_units=100)
        add_investment_to_test_account(investment)

        # Test is_expired on various dates
        with DBConnection.session() as session:
            investment = session.execute(account_investments_query).scalars().first()

            # On start date ->  not expired
            self.assertFalse(investment.is_expired)
            self.assertNotIn(investment.id, session.execute(
                account_investment_ids_query.where(Investment.is_expired)
            ).scalars().all())

            # Before start date -> not expired
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(investment.is_expired)
                self.assertNotIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_expired)
                ).scalars().all())

            # After start date -> not expired
            with time_machine.travel(start + timedelta(1)):
                self.assertFalse(investment.is_expired)
                self.assertNotIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_expired)
                ).scalars().all())

            # On End date -> expired
            with time_machine.travel(end):
                self.assertTrue(investment.is_expired)
                self.assertIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_expired)
                ).scalars().all())

            # After End date -> expired
            with time_machine.travel(end + timedelta(1)):
                self.assertTrue(investment.is_expired)
                self.assertIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_expired)
                ).scalars().all())


class ActiveProperty(EmptyAccountSetup, TestCase):
    """Test the boolean ``is_active`` hybrid property, and it's SQL expression form"""

    def test_is_active_no_investment_sus(self) -> None:
        """ Test ``is_active`` for various date ranges on an investment without any service units remaining

        On start date --> not active
        Before start date --> not active
        After start date --> not active
        On end date --> not active
        After end date --> not active

        """

        # Create the Investment and add it to the DB
        investment = Investment(start_date=start, end_date=end, current_sus=0, service_units=100, withdrawn_sus=100)
        add_investment_to_test_account(investment)

        # Test is_expired on various dates
        with DBConnection.session() as session:
            investment = session.execute(account_investments_query).scalars().first()

            # On start date -> not active
            self.assertTrue(investment.is_active)
            self.assertIn(investment.id, session.execute(
                account_investment_ids_query.where(Investment.is_active)
            ).scalars().all())

            # Before start date -> not active
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(investment.is_active)
                self.assertNotIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_active)
                ).scalars().all())

            # After start date -> not active
            with time_machine.travel(start + timedelta(1)):
                self.assertFalse(investment.is_active)
                self.assertNotIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_active)
                ).scalars().all())

            # On End date -> not active
            with time_machine.travel(end):
                self.assertFalse(investment.is_active)
                self.assertNotIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_active)
                ).scalars().all())

            # After End date -> not active
            with time_machine.travel(end + timedelta(1)):
                self.assertFalse(investment.is_active)
                self.assertNotIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_active)
                ).scalars().all())

    def test_is_active_has_investment_sus(self) -> None:
        """ Test ``is_active`` for various date ranges on an investment with service units remaining

        On start date --> active
        Before start date --> not active
        After start date --> active
        On end date --> not active
        After end date --> not active

        """

        # Create the Investment and add it to the DB
        investment = Investment(start_date=start, end_date=end, current_sus=100, service_units=100)
        add_investment_to_test_account(investment)

        # Test is_active on various dates
        with DBConnection.session() as session:
            investment = session.execute(account_investments_query).scalars().first()

            # On start date ->  active
            self.assertTrue(investment.is_active)
            self.assertIn(investment.id, session.execute(
                account_investment_ids_query.where(Investment.is_active)
            ).scalars().all())

            # Before start date -> not active
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(investment.is_active)
                self.assertNotIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_active)
                ).scalars().all())

            # After start date -> active
            with time_machine.travel(start + timedelta(1)):
                self.assertTrue(investment.is_active)
                self.assertIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_active)
                ).scalars().all())

            # On End date -> not active
            with time_machine.travel(end):
                self.assertFalse(investment.is_active)
                self.assertNotIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_active)
                ).scalars().all())

            # After End date -> not active
            with time_machine.travel(end + timedelta(1)):
                self.assertFalse(investment.is_active)
                self.assertNotIn(investment.id, session.execute(
                    account_investment_ids_query.where(Investment.is_active)
                ).scalars().all())
