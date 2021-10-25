from unittest import TestCase

from bank.dao import Account
from bank.exceptions import MissingProposalError, ProposalExistsError
from bank.orm import Session, Proposal
from bank.settings import app_settings


class CreateProposal(TestCase):
    """Tests for the creation of proposals via the ``create_proposal`` method"""

    def setUp(self) -> None:
        """Delete any proposals that may already exist for the test account"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == app_settings.test_account).delete()
            session.commit()

        self.account = Account(app_settings.test_account)

    def test_proposal_is_created(self) -> None:
        """Test a proposal is created fter the function call"""

        # Avoid false positives by checking the proposal doesn't already exist
        with self.assertRaises(MissingProposalError):
            self.account.get_proposal_info()

        self.account.create_proposal()
        self.assertTrue(self.account.get_proposal_info)

    def test_default_sus_are_zero(self) -> None:
        """Test proposals are created with zero service units by default"""

        self.account.create_proposal()
        proposal_info = self.account.get_proposal_info()
        for cluster in app_settings.clusters:
            self.assertEqual(0, proposal_info[cluster])

    def test_non_default_sus_are_set(self) -> None:
        """Tests proposal are defined the number of sus specified by kwargs"""

        self.account.create_proposal(**{c: 1000 for c in app_settings.clusters})
        proposal_info = self.account.get_proposal_info()

        for cluster in app_settings.clusters:
            self.assertEqual(1000, proposal_info[cluster])

    def test_error_if_already_exists(self) -> None:
        """Test a ``ProposalExistsError`` error is raised if the proposal already exists"""

        self.account.create_proposal()
        with self.assertRaises(ProposalExistsError):
            self.account.create_proposal()
