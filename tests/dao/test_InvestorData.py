from copy import copy
from unittest import TestCase, skip

from bank.dao import InvestorAccount
from bank.exceptions import MissingProposalError, MissingInvestmentError
from bank.orm import Session, Proposal, Investor
from bank import settings
from tests.testing_utils import InvestorSetup, ProposalSetup


class CreateInvestment(ProposalSetup, TestCase):
    """Tests for the creation of a new investment via the ``create_investment`` function"""

    def setUp(self) -> None:
        """Delete any investments that may already exist for the test account"""

        super().setUp()
        with Session() as session:
            session.query(Investor).filter(Investor.account_name == settings.test_account).delete()
            session.commit()

        self.account = InvestorAccount(settings.test_account)

    def test_investment_is_created(self) -> None:
        """Test a new investment is added to the account after the function call"""

        # Avoid false positives by checking there are no existing doesn't already exist
        original_inv = len(self.account._get_investment_info())
        self.account.create_investment(sus=1000)
        new_inv = len(self.account._get_investment_info())

        self.assertEqual(original_inv + 1, new_inv, 'Number of investments in database did not increase.')

    def test_investment_has_assigned_number_of_sus(self) -> None:
        """Test the number of assigned sus in the new investment matches kwargs in the function call"""

        test_sus = 12345
        self.account.create_investment(sus=test_sus)
        new_investment = self.account._get_investment_info()[0]
        self.assertEqual(test_sus, new_investment['service_units'])

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` exception is raised"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingProposalError):
            self.account._raise_if_missing_proposal()

        with self.assertRaises(MissingProposalError):
            self.account.create_investment(1000)

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when creating an investment with negative sus"""

        with self.assertRaises(ValueError):
            self.account.create_investment(sus=-1)


class OverwriteInvestmentSus(InvestorSetup, TestCase):
    """Test the modification of investment service units"""

    def test_sus_are_overwritten(self) -> None:
        """Test that service unit values are updated after method call"""

        for new_sus in (0, 12345):
            self.account.overwrite_investment_sus(id=self.inv_id, sus=new_sus)
            recovered_sus = self.account._get_investment_info()[0]['service_units']
            self.assertEqual(new_sus, recovered_sus)

    def test_error_on_invalid_ids(self) -> None:
        """Test an error is raised for invalid investment IDs"""

        with self.assertRaises(MissingInvestmentError):
            fake_investment_id = 312312
            self.account.overwrite_investment_sus(id=fake_investment_id, sus=12)

    def test_error_on_negative_sus(self) -> None:
        """Tests an error is raised for negative service units"""

        with self.assertRaises(ValueError):
            self.account.overwrite_investment_sus(id=self.inv_id, sus=-12)


class WithdrawFromInvestment(InvestorSetup, TestCase):
    """Tests for the withdrawal of service units from a single investment"""

    def test_investment_is_withdrawn(self) -> None:
        """Test the specified number of service units are withdrawn from the investment"""

        with Session() as session:
            investment = session.query(Investor).filter(Investor.account_name == settings.test_account).first()
            original_inv = copy(investment)

            sus_to_withdraw = 10
            withdrawn = InvestorAccount(settings.test_account)._withdraw_from_investment(investment, sus_to_withdraw)
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

            dao = InvestorAccount(settings.test_account)
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

            withdrawn = InvestorAccount(settings.test_account)._withdraw_from_investment(investment, 1)
            self.assertEqual(0, withdrawn)
            self.assertEqual(original_inv.current_sus, investment.current_sus)
            self.assertEqual(original_inv.withdrawn_sus, investment.withdrawn_sus)

    def test_error_on_nonpositive_argument(self) -> None:
        """Test an error is raised for non-positive arguments"""

        with Session() as session:
            investment = session.query(Investor).filter(Investor.account_name == settings.test_account).first()

        for sus in (0, -1):
            with self.assertRaises(ValueError):
                InvestorAccount(settings.test_account)._withdraw_from_investment(investment, sus)


@skip('Withdrawal logic has not been ported yet')
class Withdraw(InvestorSetup, TestCase):
    """Tests for the ``withdraw`` method"""

    def test_error_on_nonpositive_argument(self) -> None:
        """Test an error is raised for non-positive arguments"""

        for sus in (0, -1):
            with self.assertRaises(ValueError):
                self.account.withdraw(sus)

    def test_withdrawal_on_single_investment(self) -> None:
        raise NotImplementedError()

    def test_withdrawal_on_multiple_investments(self) -> None:
        raise NotImplementedError()

    def test_error_for_missing_investments(self) -> None:
        """Test the function fails silently if there are no investments"""

        with Session() as session:
            session.query(Investor).filter(Investor.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(ValueError):
            self.account.withdraw(10)
