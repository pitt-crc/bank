from datetime import datetime, timedelta
from unittest import TestCase

from sqlalchemy import select

from bank import settings
from bank.account_logic import InvestmentServices
from bank.exceptions import MissingInvestmentError, MissingProposalError, AccountNotFoundError
from bank.orm import Account, DBConnection, Investment
from tests._utils import InvestmentSetup, ProposalSetup

investments_query = select(Investment) \
    .join(Account) \
    .where(Account.name == settings.test_accounts[0])

primary_investment_query = investments_query.where(Investment.is_active)


class InitExceptions(InvestmentSetup, TestCase):
    """Test for errors raised during account status checks at instantiation"""

    def test_error_on_non_existent_account(self) -> None:
        # Attempt to create an investment for a nonexistent slurm account
        with self.assertRaises(AccountNotFoundError):
            self.account = InvestmentServices(account_name=settings.nonexistent_account)

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` exception is raised if the account has no proposal"""

        with self.assertRaises(MissingProposalError):
            InvestmentServices(account_name=settings.test_accounts[0])


class CreateInvestment(ProposalSetup, TestCase):
    """Tests for the creation of a new investment"""

    def test_investment_is_created(self) -> None:
        """Test a new investment is added to the account after the function call"""

        account = InvestmentServices(settings.test_accounts[0])
        account.create(sus=12345)

        with DBConnection.session() as session:
            investments = session.execute(investments_query).scalars().all()
            self.assertEqual(1, len(investments))
            self.assertEqual(12345, investments[0].service_units)

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when creating an investment with negative sus"""

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_accounts[0]).create(sus=0)

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_accounts[0]).create(sus=-1)

    def test_error_on_negative_repeat(self) -> None:
        """Test an error is raised when creating an investment with less than one repeat"""

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_accounts[0]).create(sus=1000, num_inv=0)

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_accounts[0]).create(sus=1000, num_inv=-1)

    def test_investment_is_repeated(self) -> None:
        """Test the given number of investments are created successively"""

        test_sus = 2000
        repeats = 2
        account = InvestmentServices(settings.test_accounts[0])
        account.create(sus=test_sus, num_inv=repeats)

        with DBConnection.session() as session:
            investments = session.execute(investments_query).scalars().all()
            total_sus = sum(inv.current_sus for inv in investments)

            self.assertEqual(
                repeats,
                len(investments),
                f'Expected {repeats} investments to be created but found {len(investments)}')
            self.assertEqual(test_sus, total_sus)


class DeleteInvestment(ProposalSetup, InvestmentSetup, TestCase):
    """Tests the deletion of investments with ``delete``"""

    def test_investment_is_deleted(self) -> None:
        """Test the deletion of a single investment"""

        with DBConnection.session() as session:
            investment = session.execute(primary_investment_query).scalars().first()
            primary_id = investment.id

        InvestmentServices(settings.test_accounts[0]).delete(primary_id)
        with DBConnection.session() as session:
            investment = session.execute(primary_investment_query).scalars().first()

            self.assertIsNone(investment)

    def test_delete_non_existent_investment(self) -> None:
        """Test that deleting a non-existent investment yields a MissingInvestmentError"""

        with self.assertRaises(MissingInvestmentError):
            InvestmentServices(settings.test_accounts[0]).delete(inv_id=1000)


class ModifyDate(ProposalSetup, InvestmentSetup, TestCase):
    """Test the modification of investment dates via modify_date"""

    def test_dates_are_modified(self) -> None:
        """Test start and end dates are overwritten in the investment"""

        investment_query = select(Investment).join(Account) \
            .where(Account.name == settings.test_accounts[0]) \
            .where(Investment.is_active)

        with DBConnection.session() as session:
            old_investment = session.execute(investment_query).scalars().first()
            investment_id = old_investment.id
            new_start_date = old_investment.start_date + timedelta(days=5)
            new_end_date = old_investment.end_date + timedelta(days=10)

        InvestmentServices(settings.test_accounts[0]).modify_date(investment_id, start=new_start_date, end=new_end_date)

        investment_query = select(Investment).join(Account) \
            .where(Account.name == settings.test_accounts[0]) \
            .where(Investment.id == investment_id)

        with DBConnection.session() as session:
            new_investment = session.execute(investment_query).scalars().first()
            self.assertEqual(new_start_date, new_investment.start_date)
            self.assertEqual(new_end_date, new_investment.end_date)

    def test_error_on_bad_dates(self) -> None:
        """Test a ``ValueError`` is raised when assigning chronologically wrong start/end dates"""

        investment_query = select(Investment).join(Account) \
            .where(Account.name == settings.test_accounts[0]) \
            .where(Investment.is_active)

        with DBConnection.session() as session:
            old_investment = session.execute(investment_query).scalars().first()

            start_date = old_investment.start_date
            end_date = old_investment.end_date
            bad_start_date = end_date + timedelta(days=1)
            bad_end_date = start_date - timedelta(days=1)

        # No start or end date
        self.assertFalse(
            InvestmentServices(settings.test_accounts[0]).modify_date()
        )

        # Start date after end date
        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_accounts[0]).modify_date(start=bad_start_date, end=end_date)

        # Start date after end date, providing start date alone
        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_accounts[0]).modify_date(start=bad_start_date)

        # End date before start date, providing end date alone
        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_accounts[0]).modify_date(end=bad_end_date)

    def test_error_on_bad_dates_with_id(self) -> None:
        """Test a ``ValueError`` is raised when assigning chronologically wrong start/end dates"""

        investment_query = select(Investment).join(Account) \
            .where(Account.name == settings.test_accounts[0]) \
            .where(Investment.is_active)

        with DBConnection.session() as session:
            investment = session.execute(investment_query).scalars().first()
            investment_id = investment.id
            start_date = investment.start_date
            end_date = investment.end_date
            bad_start_date = end_date + timedelta(days=1)
            bad_end_date = start_date - timedelta(days=1)

        # Attempt to modify date without specifying a date
        self.assertFalse(
            InvestmentServices(settings.test_accounts[0]).modify_date(investment_id)
        )

        # Start date after end date
        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_accounts[0]).modify_date(
                investment_id,
                bad_start_date, end_date)

        # End date before start date
        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_accounts[0]).modify_date(
                investment_id,
                start_date, bad_end_date)


class AddSus(ProposalSetup, InvestmentSetup, TestCase):
    """Tests for the addition of sus via the ``add`` method"""

    def test_sus_are_added(self) -> None:
        """Test SUs are added to the investment"""

        inv_id = 1
        sus_to_add = 1000
        InvestmentServices(settings.test_accounts[0]).add_sus(inv_id, sus_to_add)

        inv_sus_query = select(Investment.service_units).where(Investment.id == inv_id)
        with DBConnection.session() as session:
            new_sus = session.execute(inv_sus_query).scalars().first()
            self.assertEqual(self.num_inv_sus + sus_to_add, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        account = InvestmentServices(settings.test_accounts[0])
        with self.assertRaises(ValueError):
            account.add_sus(1, -1)

        with self.assertRaises(ValueError):
            account.add_sus(1, 0)


class SubtractSus(ProposalSetup, InvestmentSetup, TestCase):
    """Tests for the subtraction of sus via the ``subtract`` method"""

    def test_sus_are_subtracted(self) -> None:
        """Test SUs are removed from the proposal"""

        inv_id = 1
        sus_to_subtract = 100
        InvestmentServices(settings.test_accounts[0]).subtract_sus(inv_id, sus_to_subtract)

        inv_sus_query = select(Investment.service_units).where(Investment.id == inv_id)
        with DBConnection.session() as session:
            new_sus = session.execute(inv_sus_query).scalars().first()
            self.assertEqual(self.num_inv_sus - sus_to_subtract, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        account = InvestmentServices(settings.test_accounts[0])
        with self.assertRaises(ValueError):
            account.subtract_sus(1, -1)

        with self.assertRaises(ValueError):
            account.subtract_sus(1, 0)

    def test_error_on_over_subtract(self) -> None:
        """Test for a ``ValueError`` if more service units are subtracted than available"""

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_accounts[0]).subtract_sus(1, self.num_inv_sus + 1000)


class AdvanceInvestmentSus(ProposalSetup, InvestmentSetup, TestCase):
    """Tests for the withdrawal of service units from a single investment"""

    def setUp(self) -> None:
        super().setUp()
        self.account = InvestmentServices(settings.test_accounts[0])

    def test_investment_is_advanced(self) -> None:
        """Test the specified number of service units are advanced from the investment"""

        with DBConnection.session() as session:
            active_investment = session.execute(primary_investment_query).scalars().first()
            original_sus = active_investment.current_sus

        # Advance half the available service units
        sus_to_advance = self.num_inv_sus // 2
        self.account.advance(sus=sus_to_advance)

        with DBConnection.session() as session:
            active_investment = session.execute(primary_investment_query).scalars().first()
            new_sus = active_investment.current_sus

        self.assertEqual(new_sus, original_sus + sus_to_advance)

    def test_error_if_overdrawn(self) -> None:
        """Test an ``ValueError`` is raised if the account does not have enough SUs to cover the advance"""

        with DBConnection.session() as session:
            investments = session.execute(investments_query).scalars().all()
            available_sus = sum(inv.service_units for inv in investments)

        with self.assertRaises(ValueError):
            self.account.advance(sus=available_sus + 1)

    def test_error_on_negative_argument(self) -> None:
        """Test an ``ValueError`` is raised for negative arguments"""

        for sus in (0, -1):
            with self.assertRaises(ValueError):
                self.account.advance(sus=sus)


class MissingInvestmentErrors(ProposalSetup, TestCase):
    """Tests for errors when manipulating an account that does not have an investment"""

    def setUp(self) -> None:
        """Delete any investments that may already exist for the test account"""

        super().setUp()
        self.account = InvestmentServices(settings.test_accounts[0])

    def test_error_on_delete(self) -> None:
        """Test for a ``MissingInvestmentError`` error when deleting a missing investment"""

        with self.assertRaises(MissingInvestmentError):
            self.account.delete(inv_id=100)

    def test_error_on_modify_date(self) -> None:
        """Test a ``MissingInvestmentError`` error is raised when modifying a missing investment"""

        with self.assertRaises(MissingInvestmentError):
            self.account.modify_date(inv_id=100, start=datetime.today())

    def test_error_on_add(self) -> None:
        """Test a ``MissingInvestmentError`` error is raised when adding to a missing investment"""

        with self.assertRaises(MissingInvestmentError):
            self.account.add_sus(inv_id=100, sus=1)

    def test_error_on_subtract(self) -> None:
        """Test a ``MissingInvestmentError`` error is raised when subtracting from a missing investment"""

        with self.assertRaises(MissingInvestmentError):
            self.account.subtract_sus(inv_id=100, sus=1)

    def test_error_on_advance(self) -> None:
        """Test a ``MissingInvestmentError`` is raised if there are no investments to advance from"""

        with self.assertRaises(MissingInvestmentError):
            self.account.advance(sus=10)
