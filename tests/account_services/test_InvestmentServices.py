from datetime import timedelta
from unittest import TestCase

from bank import settings
from bank.account_services import InvestmentServices, ProposalServices
from bank.exceptions import MissingProposalError, MissingInvestmentError
from bank.orm import Session, Investment, InvestorArchive, Proposal, ProposalEnum
from tests.account_services._utils import InvestorSetup, ProposalSetup


class InitExceptions(TestCase):

    def setUp(self) -> None:
        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.commit()

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` exception is raised if the account has no proposal"""

        with self.assertRaises(MissingProposalError):
            InvestmentServices(account_name=settings.test_account)

    def test_error_proposal_is_class(self) -> None:
        """Test a ``ValueError`` is raised when managing investments for accounts with Class proposals"""

        account = ProposalServices(settings.test_account)
        account.create_proposal(type=ProposalEnum.Class)
        with self.assertRaisesRegex(ValueError, 'Investments cannot be added/managed for class accounts'):
            InvestmentServices(account_name=settings.test_account)


class CreateInvestment(ProposalSetup, TestCase):
    """Tests for the creation of a new investment via the ``create_investment`` function"""

    def setUp(self) -> None:
        """Delete any investments that may already exist for the test account"""

        super().setUp()
        with Session() as session:
            session.query(Investment).filter(Investment.account_name == settings.test_account).delete()
            session.commit()

        self.account = InvestmentServices(settings.test_account)

    def test_investment_is_created(self) -> None:
        """Test a new investment is added to the account after the function call"""

        self.account.create_investment(sus=1000)
        self.assertEqual(1, len(self.account._get_investment(self.session)))

    def test_investment_has_assigned_number_of_sus(self) -> None:
        """Test the number of assigned sus in the new investment matches kwargs in the function call"""

        test_sus = 12345
        self.account.create_investment(sus=test_sus)
        self.assertEqual(test_sus, self.account._get_investment(self.session)[0].service_units)

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when creating an investment with negative sus"""

        with self.assertRaises(ValueError):
            self.account.create_investment(sus=-1)

    def test_error_on_zero_repeat(self) -> None:
        """Test an error is raised when creating an investment with ``repeate=0``"""

        with self.assertRaises(ValueError):
            self.account.create_investment(sus=1000, num_inv=0)

    def test_investment_is_repeated(self) -> None:
        """Test the given number of investments are created successively"""

        test_sus = 2000
        repeats = 2
        self.account.create_investment(sus=test_sus, num_inv=repeats)

        with Session() as session:
            investments = session.query(Investment).filter(Investment.account_name == settings.test_account).all()
            total_sus = sum(inv.current_sus for inv in investments)

        self.assertEqual(repeats, len(investments), f'Expected {repeats} investments to be created but found {len(investments)}')
        self.assertEqual(test_sus, total_sus)


class DeleteInvestment(InvestorSetup, TestCase):
    """Tests for the deletion of investments via the ``delete_investment`` method"""

    def test_investment_is_deleted(self) -> None:
        """Test the investment is moved from the ``Investor`` to ``InvestorArchive`` table"""

        self.account.delete_investment(id=self.inv_id[0])

        investment = self.session.query(Investment).filter(Investment.id == self.inv_id[0]).first()
        self.assertIsNone(investment, 'Proposal was not deleted')

        archive = self.session.query(InvestorArchive).filter(InvestorArchive.id == self.inv_id[0]).first()
        self.assertIsNotNone(archive, 'No archive object created with matching proposal id')


class AddSus(InvestorSetup, TestCase):
    """Tests for the addition of sus via the ``add`` method"""

    def test_sus_are_added(self) -> None:
        """Test SUs are added to the investment"""

        sus_to_add = 1000
        self.account.add(self.inv_id[0], sus_to_add)
        new_sus = self.account._get_investment(self.session, self.inv_id[0]).service_units
        self.assertEqual(self.num_inv_sus + sus_to_add, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.add(self.inv_id[0], -1)

        with self.assertRaises(ValueError):
            self.account.add(self.inv_id[0], 0)


class SubtractSus(InvestorSetup, TestCase):
    """Tests for the subtraction of sus via the ``subtract`` method"""

    def test_sus_are_subtracted(self) -> None:
        """Test SUs are removed from the proposal"""

        sus_to_subtract = 10
        self.account.subtract(self.inv_id[0], sus_to_subtract)
        new_sus = self.account._get_investment(self.session, self.inv_id[0]).service_units
        self.assertEqual(self.num_inv_sus - sus_to_subtract, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.subtract(self.inv_id[0], -1)

        with self.assertRaises(ValueError):
            self.account.subtract(self.inv_id[0], 0)

    def test_error_on_over_subtract(self) -> None:
        """Test for a ``ValueError`` if more service units are subtracted than available"""

        with self.assertRaises(ValueError):
            self.account.subtract(self.inv_id[0], self.num_inv_sus + 1)


class OverwriteSus(InvestorSetup, TestCase):
    """Test the modification of allocated sus via the ``set_cluster_allocation`` method"""

    def test_sus_are_modified(self) -> None:
        """Test sus are overwritten in the investment"""

        with Session() as session:
            old_investment = self.account._get_investment(session, self.inv_id[0])

        sus_to_overwrite = 10
        self.account.overwrite(self.inv_id[0], sus_to_overwrite)
        with Session() as session:
            new_investment = self.account._get_investment(session, self.inv_id[0])

        self.assertEqual(sus_to_overwrite, new_investment.service_units)
        self.assertEqual(old_investment.start_date, old_investment.start_date)
        self.assertEqual(old_investment.end_date, old_investment.end_date)

    def test_dates_are_modified(self) -> None:
        """Test start and end dates are overwritten in the investment"""

        with Session() as session:
            old_investment = self.account._get_investment(session, self.inv_id[0])

        new_start_date = old_investment.start_date + timedelta(days=5)
        new_end_date = old_investment.end_date + timedelta(days=10)
        self.account.overwrite(self.inv_id[0], start_date=new_start_date, end_date=new_end_date)

        with Session() as session:
            new_investment = self.account._get_investment(session, self.inv_id[0])

        self.assertEqual(old_investment.service_units, new_investment.service_units)
        self.assertEqual(new_start_date, new_investment.start_date, 'Start date not overwritten with expected value')
        self.assertEqual(new_end_date, new_investment.end_date, 'End date not overwritten with expected value')

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.overwrite(self.inv_id[0], -1)

        with self.assertRaises(ValueError):
            self.account.overwrite(self.inv_id[0], 0)


class AdvanceInvestmentSus(InvestorSetup, TestCase):
    """Tests for the withdrawal of service units from a single investment"""

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
            investments = self.account._get_investment(session)
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
