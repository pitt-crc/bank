from unittest import TestCase

from bank.dao import InvestorData
from bank.exceptions import MissingProposalError
from bank.orm import Session, Investor, Proposal
from bank.settings import app_settings
from tests.dao.utils import GenericSetup


class CreateInvestment(GenericSetup, TestCase):
    """Tests for the creation of a new investment via the ``create_investment`` function"""

    def setUp(self) -> None:
        """Delete any investments that may already exist for the test account"""

        super(CreateInvestment, self).setUp()
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

    def test_raises_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` exception is raised"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == app_settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingProposalError):
            self.account._raise_if_missing_proposal()

        with self.assertRaises(MissingProposalError):
            self.account.create_investment(1000)
