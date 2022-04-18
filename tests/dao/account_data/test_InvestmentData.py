from datetime import timedelta
from unittest import TestCase

from bank import settings
from bank.dao import InvestmentData
from bank.exceptions import MissingInvestmentError
from bank.orm import Session
from tests._utils import InvestmentSetup, ProposalSetup


class CreateInvestment(ProposalSetup, TestCase):
    """Tests for the creation of a new investment via the ``self.account.create_investment`` function"""

    def test_investment_is_created(self) -> None:
        """Test a new investment is added to the account after the function call"""

        account = InvestmentData(settings.test_account)
        account.create_investment(sus=12345)
        with Session() as session:
            investments = account.get_all_investments(session)
            self.assertEqual(1, len(investments))
            self.assertEqual(12345, investments[0].service_units)

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when creating an investment with negative sus"""

        with self.assertRaises(ValueError):
            InvestmentData(settings.test_account).create_investment(sus=-1)

    def test_error_on_zero_repeat(self) -> None:
        """Test an error is raised when creating an investment with ``repeate=0``"""

        with self.assertRaises(ValueError):
            InvestmentData(settings.test_account).create_investment(sus=1000, num_inv=0)

    def test_investment_is_repeated(self) -> None:
        """Test the given number of investments are created successively"""

        test_sus = 2000
        repeats = 2
        account = InvestmentData(settings.test_account)
        account.create_investment(sus=test_sus, num_inv=repeats)

        with Session() as session:
            investments = account.get_all_investments(session)
            total_sus = sum(inv.current_sus for inv in investments)

            self.assertEqual(repeats, len(investments), f'Expected {repeats} investments to be created but found {len(investments)}')
            self.assertEqual(test_sus, total_sus)


class DeleteInvestment(InvestmentSetup, TestCase):

    def test_investment_is_deleted(self) -> None:
        account = InvestmentData(settings.test_account)
        with Session() as session:
            account.get_investment(session, 1)

        account.delete_investment(id=1)
        with Session() as session:
            with self.assertRaises(MissingInvestmentError):
                account.get_investment(session, 1)


class AddSus(InvestmentSetup, TestCase):
    """Tests for the addition of sus via the ``add`` method"""

    def test_sus_are_added(self) -> None:
        """Test SUs are added to the investment"""

        sus_to_add = 1000
        account = InvestmentData(settings.test_account)

        inv_id = 1
        account.add_sus(inv_id, sus_to_add)
        with Session() as session:
            new_sus = account.get_investment(session, inv_id).service_units
            self.assertEqual(self.num_inv_sus + sus_to_add, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        account = InvestmentData(settings.test_account)
        with self.assertRaises(ValueError):
            account.add_sus(1, -1)

        with self.assertRaises(ValueError):
            account.add_sus(1, 0)


class SubtractSus(InvestmentSetup, TestCase):
    """Tests for the subtraction of sus via the ``subtract`` method"""

    def test_sus_are_subtracted(self) -> None:
        """Test SUs are removed from the proposal"""

        sus_to_subtract = 10
        account = InvestmentData(settings.test_account)
        account.subtract(1, sus_to_subtract)
        with Session() as session:
            new_sus = account.get_investment(session, 1).service_units
            self.assertEqual(self.num_inv_sus - sus_to_subtract, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        account = InvestmentData(settings.test_account)
        with self.assertRaises(ValueError):
            account.subtract(1, -1)

        with self.assertRaises(ValueError):
            account.subtract(1, 0)

    def test_error_on_over_subtract(self) -> None:
        """Test for a ``ValueError`` if more service units are subtracted than available"""

        with self.assertRaises(ValueError):
            InvestmentData(settings.test_account).subtract(1, self.num_inv_sus + 1000)


class OverwriteSus(InvestmentSetup, TestCase):
    """Test the modification of allocated sus via the ``set_cluster_allocation`` method"""

    def test_sus_are_modified(self) -> None:
        """Test sus are overwritten in the investment"""

        account = InvestmentData(settings.test_account)
        with Session() as session:
            old_investment = account.get_investment(session, 1)

        sus_to_overwrite = 10
        account.overwrite(1, sus_to_overwrite)
        with Session() as session:
            new_investment = account.get_investment(session, 1)

        self.assertEqual(sus_to_overwrite, new_investment.service_units)
        self.assertEqual(old_investment.start_date, old_investment.start_date)
        self.assertEqual(old_investment.end_date, old_investment.end_date)

    def test_dates_are_modified(self) -> None:
        """Test start and end dates are overwritten in the investment"""

        account = InvestmentData(settings.test_account)
        with Session() as session:
            old_investment = account.get_investment(session, 1)

        new_start_date = old_investment.start_date + timedelta(days=5)
        new_end_date = old_investment.end_date + timedelta(days=10)
        account.overwrite(1, start_date=new_start_date, end_date=new_end_date)

        with Session() as session:
            new_investment = account.get_investment(session, 1)

        self.assertEqual(old_investment.service_units, new_investment.service_units)
        self.assertEqual(new_start_date, new_investment.start_date, 'Start date not overwritten with expected value')
        self.assertEqual(new_end_date, new_investment.end_date, 'End date not overwritten with expected value')

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        account = InvestmentData(settings.test_account)
        with self.assertRaises(ValueError):
            account.overwrite(1, -1)

        with self.assertRaises(ValueError):
            account.overwrite(1, 0)
