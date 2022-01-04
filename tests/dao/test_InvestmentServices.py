from unittest import TestCase

from bank import settings
from bank.dao import InvestmentServices
from bank.exceptions import MissingProposalError, MissingInvestmentError
from bank.orm import Session, Proposal, Investor, InvestorArchive
from tests.dao._utils import InvestorSetup, ProposalSetup


class CreateInvestment(ProposalSetup, TestCase):
    """Tests for the creation of a new investment via the ``create_investment`` function"""

    def setUp(self) -> None:
        """Delete any investments that may already exist for the test account"""

        super().setUp()
        with Session() as session:
            session.query(Investor).filter(Investor.account_name == settings.test_account).delete()
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

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` exception is raised"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingProposalError):
            self.account.create_investment(1000)

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when creating an investment with negative sus"""

        with self.assertRaises(ValueError):
            self.account.create_investment(sus=-1)

    def test_error_on_zero_repeat(self) -> None:
        """Test an error is raised when creating an investment with ``repeate=0``"""

        with self.assertRaises(ValueError):
            self.account.create_investment(sus=1000, num_inv=0)

    def test_investment_is_repeated(self) -> None:
        test_sus = 2000
        repeats = 2
        self.account.create_investment(sus=test_sus, num_inv=repeats)

        with Session() as session:
            investments = session.query(Investor).filter(Investor.account_name == settings.test_account).all()
            total_sus = sum(inv.current_sus for inv in investments)

        self.assertEqual(repeats, len(investments), f'Expected {repeats} investments to be created but found {len(investments)}')
        self.assertEqual(test_sus, total_sus)


class DeleteInvestment(InvestorSetup, TestCase):
    """Tests for the deletion of investments via the ``delete_investment`` method"""

    def test_investment_is_deleted(self) -> None:
        """Test the investment is moved from the ``Investor`` to ``InvestorArchive`` table"""

        self.account.delete_investment(id=self.inv_id)

        investment = self.session.query(Investor).filter(Investor.id == self.inv_id).first()
        self.assertIsNone(investment, 'Proposal was not deleted')

        archive = self.session.query(InvestorArchive).filter(InvestorArchive.id == self.inv_id).first()
        self.assertIsNotNone(archive, 'No archive object created with matching proposal id')


class AddSus(InvestorSetup, TestCase):
    """Tests for the addition of sus via the ``add`` method"""

    def test_sus_are_added(self) -> None:
        """Test SUs are added to the investment"""

        sus_to_add = 1000
        self.account.add(self.inv_id, sus_to_add)
        new_sus = self.account._get_investment(self.session, self.inv_id).service_units
        self.assertEqual(self.num_inv_sus + sus_to_add, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.add(self.inv_id, -1)

        with self.assertRaises(ValueError):
            self.account.add(self.inv_id, 0)


class SubtractSus(InvestorSetup, TestCase):
    """Tests for the subtraction of sus via the ``subtract`` method"""

    def test_sus_are_subtracted(self) -> None:
        """Test SUs are removed from the proposal"""

        sus_to_subtract = 10
        self.account.subtract(self.inv_id, sus_to_subtract)
        new_sus = self.account._get_investment(self.session, self.inv_id).service_units
        self.assertEqual(self.num_inv_sus - sus_to_subtract, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.subtract(self.inv_id, -1)

        with self.assertRaises(ValueError):
            self.account.subtract(self.inv_id, 0)

    def test_error_on_over_subtract(self) -> None:
        """Test for a ``ValueError`` if more service units are subtracted than available"""

        with self.assertRaises(ValueError):
            self.account.subtract(self.inv_id, self.num_inv_sus + 1)


class OverwriteSus(InvestorSetup, TestCase):
    """Test the modification of allocated sus via the ``set_cluster_allocation`` method"""

    def test_sus_are_modified(self) -> None:
        """Test sus from kwargs are set in the proposal"""

        sus_to_overwrite = 10
        self.account.overwrite(self.inv_id, sus_to_overwrite)
        new_sus = self.account._get_investment(self.session, self.inv_id).service_units
        self.assertEqual(sus_to_overwrite, new_sus)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.overwrite(self.inv_id, -1)

        with self.assertRaises(ValueError):
            self.account.overwrite(self.inv_id, 0)


class AdvanceInvestmentSus(ProposalSetup, TestCase):
    """Tests for the withdrawal of service units from a single investment"""

    def setUp(self) -> None:
        super().setUp()

        # Create a series of three investments totalling 3,000 service units
        self.account = InvestmentServices(settings.test_account)
        self.account.create_investment(3_000, num_inv=3)

    def test_investment_is_advanced(self) -> None:
        """Test the specified number of service units are advanced from the investment"""

        # Advance half the available service units
        self.account.advance(1_500)

        with Session() as session:
            investments = session.query(Investor) \
                .filter(Investor.account_name == settings.test_account) \
                .order_by(Investor.start_date) \
                .all()

        # Oldest investment should be untouched
        self.assertEqual(1_000, investments[0].service_units)
        self.assertEqual(2500, investments[0].current_sus)
        self.assertEqual(0, investments[0].withdrawn_sus)

        # Middle investment should be partially withdrawn
        self.assertEqual(1_000, investments[1].service_units)
        self.assertEqual(500, investments[1].current_sus)
        self.assertEqual(500, investments[1].withdrawn_sus)

        # Youngest (i.e., latest starting time) investment should be fully withdrawn
        self.assertEqual(1_000, investments[2].service_units)
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
            session.query(Investor).filter(Investor.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingInvestmentError):
            self.account.advance(10)
