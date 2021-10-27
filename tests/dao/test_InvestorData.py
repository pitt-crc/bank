from unittest import TestCase

from bank.dao import InvestorData
from bank.exceptions import MissingProposalError
from bank.orm import Session, Proposal, Investor
from bank.settings import app_settings
from tests.dao.utils import InvestorSetup


class CreateInvestment(TestCase):
    """Tests for the creation of a new investment via the ``create_investment`` function"""

    def setUp(self) -> None:
        """Delete any investments that may already exist for the test account"""

        with Session() as session:
            session.query(Investor).filter(Investor.account_name == app_settings.test_account).delete()
            session.commit()

        self.account = InvestorData(app_settings.test_account)

    def test_investment_is_created(self) -> None:
        """Test a new investment is added to the account after the function call"""

        # Avoid false positives by checking there are no existing doesn't already exist
        original_inv = len(self.account.get_investment_info())
        self.account.create_investment(sus=1000)
        new_inv = len(self.account.get_investment_info())

        self.assertEqual(original_inv + 1, new_inv, 'Number of investments in database did not increase.')

    def test_investment_has_assigned_number_of_sus(self) -> None:
        """Test the number of assigned sus in the new investment matches kwargs in the function call"""

        test_sus = 12345
        self.account.create_investment(sus=test_sus)
        new_investment = self.account.get_investment_info()[0]
        self.assertEqual(test_sus, new_investment['service_units'])

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` exception is raised"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == app_settings.test_account).delete()
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

        new_sus = 12345
        inv_id = self.account.get_investment_info()[0]['id']

        self.account.overwrite_investment_sus(**{str(inv_id): new_sus})
        recovered_sus = self.account.get_investment_info()[0]['service_units']
        self.assertEqual(new_sus, recovered_sus)
