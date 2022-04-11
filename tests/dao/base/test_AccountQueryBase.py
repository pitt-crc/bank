from unittest import TestCase

from bank import settings
from bank.dao import AccountQueryBase
from bank.exceptions import *
from bank.orm import Session
from tests._utils import EmptyAccountSetup, ProposalSetup


class GetAccount(EmptyAccountSetup, TestCase):
    """Tests for the ``get_account`` method"""

    def test_returned_record_matches_account_name(self) -> None:
        """Test the returned DB record matches the account name"""

        with Session() as session:
            account = AccountQueryBase(settings.test_account).get_account(session)

        self.assertEqual(account.name, settings.test_account)

    def test_error_on_missing_account(self) -> None:
        """Test for an ``AccountNotFoundError`` if an account does not exist"""

        with self.assertRaises(BankAccountNotFoundError), Session() as session:
            AccountQueryBase('fake_account_name').get_account(session)


class GetPrimaryProposal(ProposalSetup, TestCase):
    """Tests for the ``get_primary_proposal`` method"""

    def test_returned_proposal_is_active(self) -> None:
        """Test the returned proposal is marked as active"""

        with Session() as session:
            proposal = AccountQueryBase(settings.test_account).get_primary_proposal(session)

        self.assertTrue(proposal.is_active)

    def test_error_on_no_active_proposal(self):
        """Test for a ``MissingProposalError`` if there is no active proposal"""

        # Delete any account proposals
        EmptyAccountSetup.setUp(self)
        with self.assertRaises(MissingProposalError), Session() as session:
            AccountQueryBase(settings.test_account).get_primary_proposal(session)


class GetProposalById(ProposalSetup, TestCase):
    """Tests for the ``get_proposal_by_id`` method"""

    def test_returned_proposal_matches_id(self) -> None:
        """Test returned proposals match the requested id(s)"""

        qb = AccountQueryBase(settings.test_account)
        with Session() as session:
            proposal1 = qb.get_proposal_by_id(session, 1)
            proposal2 = qb.get_proposal_by_id(session, 2)

        self.assertEqual(1, proposal1.id)
        self.assertEqual(2, proposal2.id)

    def test_error_on_no_proposal_found(self):
        """Test for a ``MissingProposalError` error` when proposal id does not exist"""

        qb = AccountQueryBase(settings.test_account)
        with self.assertRaises(MissingProposalError), Session() as session:
            qb.get_proposal_by_id(session, 1000)

    def test_error_on_no_proposal_for_account(self):
        """Test for a ``MissingProposalError` error` when given proposal id for another account"""

        # Ensure the proposal id used in testing does exist
        with Session() as session:
            qb = AccountQueryBase(settings.test_account)
            qb.get_proposal_by_id(session, 1)

        # Check for error when trying to access proposal id from a different account
        qb = AccountQueryBase('fake_account')
        with self.assertRaises(MissingProposalError), Session() as session:
            qb.get_proposal_by_id(session, 1)


class GetAllProposals(ProposalSetup, TestCase):
    """Tests for the ``get_all_proposals`` method"""

    def test_returned_all_proposals_for_account(self) -> None:
        """Compare number of returned proposals against number created during test setup"""

        # Compare number of returned proposals with the number set up by the test suite
        # See ``ProposalSetup.setUp`` for more details
        with Session() as session:
            proposals = AccountQueryBase(settings.test_account).get_all_proposals(session)
            self.assertEqual(3, len(proposals))

    def test_no_error_on_empty_list(self) -> None:
        """Test no error is raised for an account with no proposals"""

        # Delete any account proposals
        EmptyAccountSetup.setUp(self)
        with Session() as session:
            proposals = AccountQueryBase(settings.test_account).get_all_proposals(session)
            self.assertEqual([], proposals)
