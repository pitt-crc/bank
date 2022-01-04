from copy import copy
from unittest import TestCase, skip

from bank import settings
from bank.dao import InvestmentServices
from bank.exceptions import MissingProposalError
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


@skip('Logic being tested is not finished being implemented')
class AdvanceInvestmentSus(InvestorSetup, TestCase):
    """Tests for the withdrawal of service units from a single investment"""

    def test_investment_is_withdrawn(self) -> None:
        """Test the specified number of service units are withdrawn from the investment"""

        with Session() as session:
            investment = session.query(Investor).filter(Investor.account_name == settings.test_account).first()
            original_inv = copy(investment)

            sus_to_withdraw = 10
            withdrawn = InvestmentServices(settings.test_account)._withdraw_from_investment(investment, sus_to_withdraw)
            self.assertEqual(sus_to_withdraw, withdrawn)

            self.assertEqual(original_inv.current_sus + sus_to_withdraw, investment.current_sus)
            self.assertEqual(original_inv.withdrawn_sus + sus_to_withdraw, investment.withdrawn_sus)
            self.assertEqual(original_inv.service_units, investment.service_units)

    def test_investment_with_existing_withdrawal(self) -> None:
        """Test the number of withdrawn service units does not exceed available balance"""

        with Session() as session:
            investment = session.query(Investor).filter(Investor.account_name == settings.test_account).first()
            service_units = investment.service_units
            half_service_units = service_units / 2

            dao = InvestmentServices(settings.test_account)
            first_withdraw = dao._withdraw_from_investment(investment, half_service_units)
            second_withdraw = dao._withdraw_from_investment(investment, service_units)
            self.assertEqual(half_service_units, first_withdraw)
            self.assertEqual(half_service_units, second_withdraw)

    def test_return_zero_if_overdrawn(self) -> None:
        """Test the number of withdrawn service units is zero if the account is already overdrawn"""

        with Session() as session:
            investment = session.query(Investor).filter(Investor.account_name == settings.test_account).first()
            investment.withdrawn_sus = investment.service_units
            original_inv = copy(investment)

            withdrawn = InvestmentServices(settings.test_account)._withdraw_from_investment(investment, 1)
            self.assertEqual(0, withdrawn)
            self.assertEqual(original_inv.current_sus, investment.current_sus)
            self.assertEqual(original_inv.withdrawn_sus, investment.withdrawn_sus)

    def test_error_on_nonpositive_argument(self) -> None:
        """Test an error is raised for non-positive arguments"""

        with Session() as session:
            investment = session.query(Investor).filter(Investor.account_name == settings.test_account).first()

        for sus in (0, -1):
            with self.assertRaises(ValueError):
                InvestmentServices(settings.test_account)._withdraw_from_investment(investment, sus)

    def test_error_for_missing_investments(self) -> None:
        """Test the function fails silently if there are no investments"""

        with Session() as session:
            session.query(Investor).filter(Investor.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(ValueError):
            self.account.withdraw(10)
