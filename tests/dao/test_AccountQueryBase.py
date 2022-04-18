from unittest import TestCase

from bank import settings
from bank.dao import AccountQueryBase
from bank.exceptions import *
from bank.orm import Session
from tests._utils import EmptyAccountSetup, ProposalSetup, InvestmentSetup


class GetAccount(EmptyAccountSetup, TestCase):
    """Tests retrieval of ``account`` records"""

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
    """Tests retrieval of the currently active proposal"""

    def test_returned_proposal_is_active(self) -> None:
        """Test the returned proposal is marked as active"""

        with Session() as session:
            proposal = AccountQueryBase(settings.test_account).get_primary_proposal(session)
            self.assertTrue(proposal.is_active)

    def test_error_no_active_proposal(self) -> None:
        """Test for a ``MissingProposalError`` if there is no active proposal"""

        # Delete any account proposals
        EmptyAccountSetup.setUp(self)
        with self.assertRaises(MissingProposalError), Session() as session:
            AccountQueryBase(settings.test_account).get_primary_proposal(session)


class GetProposalById(ProposalSetup, TestCase):
    """Test the retrieval of proposals by ID"""

    def test_returned_proposal_matches_id(self) -> None:
        """Test returned proposal matches the requested id"""

        qb = AccountQueryBase(settings.test_account)
        with Session() as session:
            proposal1 = qb.get_proposal_by_id(session, 1)
            proposal2 = qb.get_proposal_by_id(session, 2)

        self.assertEqual(1, proposal1.id)
        self.assertEqual(2, proposal2.id)

    def test_error_no_proposal_found(self) -> None:
        """Test for a ``MissingProposalError`` error when proposal id does not exist"""

        qb = AccountQueryBase(settings.test_account)
        with self.assertRaises(MissingProposalError), Session() as session:
            qb.get_proposal_by_id(session, 1000)

    def test_error_no_proposal_for_account(self) -> None:
        """Test for a ``MissingProposalError`` error when given proposal id for another account"""

        # Ensure the proposal id used in testing does exist
        with Session() as session:
            qb = AccountQueryBase(settings.test_account)
            qb.get_proposal_by_id(session, 1)

        # Check for error when trying to access proposal id from a different account
        qb = AccountQueryBase('fake_account')
        with self.assertRaises(MissingProposalError), Session() as session:
            qb.get_proposal_by_id(session, 1)


class GetAllProposals(ProposalSetup, TestCase):
    """Test the retrieval of all proposals tied to an account"""

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


class GetPrimaryInvestment(InvestmentSetup, TestCase):
    """Tests retrieval of the currently active investment"""

    def test_returned_investment_is_active(self) -> None:
        """Test the returned record is marked as active"""

        with Session() as session:
            inv = AccountQueryBase(settings.test_account).get_primary_investment(session)
            self.assertTrue(inv.is_active)

    def test_error_no_account_investments(self) -> None:
        """Test for a ``MissingInvestmentError`` error when account has no primary investment"""

        EmptyAccountSetup.setUp(self)
        with self.assertRaises(MissingInvestmentError), Session() as session:
            AccountQueryBase(settings.test_account).get_primary_investment(session)


class GetInvestmentById(InvestmentSetup, TestCase):
    """Test the retrieval of investments by ID"""

    def test_returned_investment_matches_id(self) -> None:
        """Test returned investments match the requested id(s)"""

        qb = AccountQueryBase(settings.test_account)
        with Session() as session:
            investment1 = qb.get_investment_by_id(session, 1)
            investment2 = qb.get_investment_by_id(session, 2)

        self.assertEqual(1, investment1.id)
        self.assertEqual(2, investment2.id)

    def test_error_no_investment_found(self) -> None:
        """Test for a ``MissingInvestmentError`` error when investment id does not exist"""

        qb = AccountQueryBase(settings.test_account)
        with self.assertRaises(MissingInvestmentError), Session() as session:
            qb.get_investment_by_id(session, 1000)

    def test_error_no_investment_for_account(self) -> None:
        """Test for a ``MissingInvestmentError`` error when given investment id for another account"""

        qb = AccountQueryBase('fake_account')
        with self.assertRaises(MissingInvestmentError), Session() as session:
            qb.get_investment_by_id(session, 1)


class GetAllInvestments(InvestmentSetup, TestCase):
    """Test the retrieval of all investments tied to an account"""

    def test_returned_all_investments_for_account(self) -> None:
        """Compare number of returned investments against number created during test setup"""

        with Session() as session:
            investments = AccountQueryBase(settings.test_account).get_all_investments(session)
            self.assertEqual(3, len(investments))

    def test_no_error_on_empty_list(self) -> None:
        """Test no error is raised for an account with no investments"""

        # Delete any account proposals
        ProposalSetup.setUp(self)
        with Session() as session:
            investments = AccountQueryBase(settings.test_account).get_all_investments(session)
            self.assertEqual([], investments)
