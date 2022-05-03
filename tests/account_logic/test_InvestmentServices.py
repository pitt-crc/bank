from datetime import timedelta
from unittest import TestCase

from sqlalchemy import select

from bank import settings
from bank.account_logic import InvestmentServices, ProposalServices
from bank.exceptions import MissingInvestmentError, MissingProposalError
from bank.orm import ProposalEnum, Investment, Session, Account
from tests._utils import InvestmentSetup, ProposalSetup, EmptyAccountSetup

investments_query = select(Investment) \
    .join(Account) \
    .where(Account.name == settings.test_account)

primary_investment_query = investments_query.where(Investment.is_active == True)


class InitExceptions(InvestmentSetup, TestCase):
    """Test for errors raised during account status checks at instantiation"""

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` exception is raised if the account has no proposal"""

        with self.assertRaises(MissingProposalError):
            InvestmentServices(account_name=settings.test_account)

    def test_error_proposal_is_class(self) -> None:
        """Test a ``ValueError`` is raised when managing investments for accounts with Value2 proposals"""

        ProposalServices(settings.test_account).create_proposal(type=ProposalEnum.Class)
        with self.assertRaisesRegex(ValueError, 'Investments cannot be added/managed for class accounts'):
            InvestmentServices(account_name=settings.test_account)


class CreateInvestment(ProposalSetup, TestCase):
    """Tests for the creation of a new investment"""

    def test_investment_is_created(self) -> None:
        """Test a new investment is added to the account after the function call"""

        account = InvestmentServices(settings.test_account)
        account.create_investment(sus=12345)

        with Session() as session:
            investments = session.execute(investments_query).scalars().all()
            self.assertEqual(1, len(investments))
            self.assertEqual(12345, investments[0].service_units)

    def test_error_on_nonpositive_sus(self) -> None:
        """Test an error is raised when creating an investment with non-positive sus"""

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_account).create_investment(sus=0)

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_account).create_investment(sus=-1)

    def test_error_on_nonpositive_repeate(self) -> None:
        """Test an error is raised when creating an investment with less than one repeat"""

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_account).create_investment(sus=1000, num_inv=0)

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_account).create_investment(sus=1000, num_inv=-1)

    def test_investment_is_repeated(self) -> None:
        """Test the given number of investments are created successively"""

        test_sus = 2000
        repeats = 2
        account = InvestmentServices(settings.test_account)
        account.create_investment(sus=test_sus, num_inv=repeats)

        with Session() as session:
            investments = session.execute(investments_query).scalars().all()
            total_sus = sum(inv.current_sus for inv in investments)

            self.assertEqual(repeats, len(investments), f'Expected {repeats} investments to be created but found {len(investments)}')
            self.assertEqual(test_sus, total_sus)


class DeleteInvestment(ProposalSetup, InvestmentSetup, TestCase):

    def test_investment_is_deleted(self) -> None:
        with Session() as session:
            investment = session.execute(primary_investment_query).scalars().first()
            primary_id = investment.id

        InvestmentServices(settings.test_account).delete_investment(primary_id)
        with Session() as session:
            investment = session.execute(primary_investment_query).scalars().first()
            self.assertIsNone(investment)


class AddSus(ProposalSetup, InvestmentSetup, TestCase):
    """Tests for the addition of sus via the ``add`` method"""

    def test_sus_are_added(self) -> None:
        """Test SUs are added to the investment"""

        sus_to_add = 1000
        account = InvestmentServices(settings.test_account)

        inv_id = 1
        account.add_sus(inv_id, sus_to_add)
        with Session() as session:
            new_sus = account.get_investment(session, inv_id).service_units
            self.assertEqual(self.num_inv_sus + sus_to_add, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        account = InvestmentServices(settings.test_account)
        with self.assertRaises(ValueError):
            account.add_sus(1, -1)

        with self.assertRaises(ValueError):
            account.add_sus(1, 0)


class SubtractSus(ProposalSetup, InvestmentSetup, TestCase):
    """Tests for the subtraction of sus via the ``subtract`` method"""

    def test_sus_are_subtracted(self) -> None:
        """Test SUs are removed from the proposal"""

        sus_to_subtract = 10
        account = InvestmentServices(settings.test_account)
        account.subtract(1, sus_to_subtract)
        with Session() as session:
            new_sus = account.get_investment(session, 1).service_units
            self.assertEqual(self.num_inv_sus - sus_to_subtract, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        account = InvestmentServices(settings.test_account)
        with self.assertRaises(ValueError):
            account.subtract(1, -1)

        with self.assertRaises(ValueError):
            account.subtract(1, 0)

    def test_error_on_over_subtract(self) -> None:
        """Test for a ``ValueError`` if more service units are subtracted than available"""

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_account).subtract(1, self.num_inv_sus + 1000)


class OverwriteSus(ProposalSetup, InvestmentSetup, TestCase):
    """Test the modification of allocated sus via the ``set_cluster_allocation`` method"""

    def test_sus_are_modified(self) -> None:
        """Test sus are overwritten in the investment"""

        account = InvestmentServices(settings.test_account)
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

        account = InvestmentServices(settings.test_account)
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

        account = InvestmentServices(settings.test_account)
        with self.assertRaises(ValueError):
            account.overwrite(1, -1)

        with self.assertRaises(ValueError):
            account.overwrite(1, 0)


class AdvanceInvestmentSus(ProposalSetup, InvestmentSetup, TestCase):
    """Tests for the withdrawal of service units from a single investment"""

    def setUp(self) -> None:
        self.account = InvestmentServices(settings.test_account)

    def test_investment_is_advanced(self) -> None:
        """Test the specified number of service units are advanced from the investment"""

        # Advance half the available service units
        self.account.advance(1_500)

        with Session() as session:
            investments = session.query(Investment) \
                .filter(Investment.account_name == settings.test_account) \
                .order_by(Investment.start_date) \
                .all()

        # Oldest investment should be untouched
        self.assertEqual(self.num_inv_sus, investments[0].service_units)
        self.assertEqual(2500, investments[0].current_sus)
        self.assertEqual(0, investments[0].withdrawn_sus)

        # Middle investment should be partially withdrawn
        self.assertEqual(self.num_inv_sus, investments[1].service_units)
        self.assertEqual(500, investments[1].current_sus)
        self.assertEqual(500, investments[1].withdrawn_sus)

        # Youngest (i.e., latest starting time) investment should be fully withdrawn
        self.assertEqual(self.num_inv_sus, investments[2].service_units)
        self.assertEqual(0, investments[2].current_sus)
        self.assertEqual(1_000, investments[2].withdrawn_sus)

    def test_error_if_overdrawn(self) -> None:
        """Test an ``ValueError`` is raised if the account does not have enough SUs to cover the advance"""

        with Session() as session:
            investments = self.account.get_all_investments(session)
            available_sus = sum(inv.service_units for inv in investments)

        with self.assertRaises(ValueError):
            InvestmentServices(settings.test_account).advance(available_sus + 1)

    def test_error_on_nonpositive_argument(self) -> None:
        """Test an ``ValueError`` is raised for non-positive arguments"""

        for sus in (0, -1):
            with self.assertRaises(ValueError):
                InvestmentServices(settings.test_account).advance(sus)

    def test_error_for_missing_investments(self) -> None:
        """Test a ``MissingInvestmentError`` is raised if there are no investments"""

        with Session() as session:
            session.query(Investment).filter(Investment.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingInvestmentError):
            self.account.advance(10)


class MissingInvetmentErrors(ProposalSetup, TestCase):
    """Tests for errors when manipulating an account that does not have a investment"""

    def setUp(self) -> None:
        """Delete any investments that may already exist for the test account"""

        super().setUp()
        self.account = InvestmentServices(settings.test_account)

    def test_error_on_delete(self) -> None:
        """Test for a ``MissingInvestmentError`` error when deleting a missing investment"""

        with self.assertRaises(MissingInvestmentError):
            self.account.delete_investment()

    def test_error_on_modify(self) -> None:
        """Test a ``MissingInvestmentError`` error is raised when modifying a missing investment"""

        with self.assertRaises(MissingInvestmentError):
            self.account.modify_investment(**{settings.test_cluster: 1, 'pid': 1000})

    def test_error_on_add(self) -> None:
        """Test a ``MissingInvestmentError`` error is raised when adding to a missing investment"""

        with self.assertRaises(MissingInvestmentError):
            self.account.add_sus(**{settings.test_cluster: 1})

    def test_error_on_subtract(self) -> None:
        """Test a ``MissingInvestmentError`` error is raised when subtracting from a missing investment"""

        with self.assertRaises(MissingInvestmentError):
            self.account.subtract_sus(**{settings.test_cluster: 1})


class PreventOverlappingInvestments(EmptyAccountSetup, TestCase):
    """Tests to ensure investments cannot overlap in time"""

    def test_error_on_investment_creation(self):
        """Test new investments are not allowed to overlap with existing investments"""

        raise NotImplementedError

    def test_error_on_investment_modification(self):
        """Test existing investments can not be modified to overlap with other investments"""

        raise NotImplementedError
