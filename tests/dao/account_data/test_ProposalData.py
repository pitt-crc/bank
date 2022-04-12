from datetime import timedelta
from unittest import TestCase

from bank import settings
from bank.dao import ProposalData
from bank.exceptions import MissingProposalError, ProposalExistsError
from bank.orm import Session, Proposal
from tests._utils import ProposalSetup, EmptyAccountSetup


class CreateProposal(EmptyAccountSetup, TestCase):
    """Test the creation of proposals via the ``create_proposal`` method"""

    def setUp(self) -> None:
        """Delete any proposals that may already exist for the test account"""

        super().setUp()
        self.account = ProposalData(settings.test_account)

    def test_proposal_is_created(self) -> None:
        """Test a proposal is created after the function call"""

        self.account.create_proposal()
        with Session() as session:
            self.assertTrue(self.account.get_primary_proposal(session))

    def test_default_sus_are_zero(self) -> None:
        """Test proposals are created with zero service units by default"""

        self.account.create_proposal()
        with Session() as session:
            allocations = self.account.get_proposal(session).allocations
            self.assertTrue(allocations)
            for alloc in allocations:
                self.assertEqual(0, alloc.service_units)

    def test_non_default_sus_are_set(self) -> None:
        """Test proposals are assigned the number of sus specified by kwargs"""

        self.account.create_proposal(**{settings.test_cluster: 1000})
        with Session() as session:
            allocation = self.account.get_proposal(session).allocations[0]
            self.assertEqual(settings.test_cluster, allocation.cluster_name)
            self.assertEqual(1000, allocation.service_units)

    def test_error_if_already_exists(self) -> None:
        """Test a ``ProposalExistsError`` error is raised if the proposal already exists"""

        self.account.create_proposal()
        with self.assertRaises(ProposalExistsError):
            self.account.create_proposal()

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.create_proposal(**{settings.test_cluster: -1})


class DeleteProposal(ProposalSetup, TestCase):
    """Tests for the deletion of proposals via the ``delete_proposal`` method"""

    def test_primary_proposal_is_deleted(self) -> None:
        # Make sure a primary proposal exists
        account = ProposalData(settings.test_account)
        account.delete_proposal()
        with self.assertRaises(MissingProposalError, 'Primary proposal was not deleted'), Session() as session:
            account.get_proposal(session)

    def test_proposal_is_deleted_by_id(self) -> None:
        account = ProposalData(settings.test_account)
        with Session() as session:
            for p in account.get_all_proposals(session):
                account.delete_proposal(pid=p.id)

        with Session() as session:
            self.assertFalse(account.get_all_proposals(session), 'Not all proposals were deleted by their ID')

    def test_error_if_missing_primary_proposal(self) -> None:
        """Test a ``MissingProposalError`` error is raised if there is no primary proposal"""

        EmptyAccountSetup.setUp(self)
        with self.assertRaises(MissingProposalError):
            ProposalData(settings.test_account).delete_proposal()

    def test_error_if_missing_proposal_id(self) -> None:
        """Test a ``MissingProposalError`` error is raised if there is no proposal with a given ID"""

        with self.assertRaises(MissingProposalError):
            ProposalData(settings.test_account).delete_proposal(pid=1000)


class AddSus(ProposalSetup, TestCase):
    """Tests for the addition of sus via the ``add`` method"""

    def test_sus_are_added(self) -> None:
        """Test SUs are added to the proposal"""

        sus_to_add = 1000
        self.account.add(**{settings.test_cluster: sus_to_add})
        with Session() as session:
            proposal = self.account.get_proposal(session)
            new_sus = getattr(proposal, settings.test_cluster)

        self.assertEqual(self.num_proposal_sus + sus_to_add, new_sus)

    def test_error_on_bad_cluster_name(self) -> None:
        """Test a ``ValueError`` is raised if the cluster name is not defined in application settings"""

        fake_cluster_name = 'fake_cluster'
        with self.assertRaisesRegex(ValueError, f'Cluster {fake_cluster_name} is not defined*'):
            self.account.add(**{fake_cluster_name: 1000})

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.add(**{settings.test_cluster: -1})

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` error is raised when account has no proposal"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingProposalError):
            self.account.add(**{settings.test_cluster: -1})


class SubtractSus(ProposalSetup, TestCase):
    """Tests for the subtraction of sus via the ``subtract`` method"""

    def test_sus_are_subtracted(self) -> None:
        """Test SUs are removed from the proposal"""

        sus_to_subtract = 10
        self.account.subtract(**{settings.test_cluster: sus_to_subtract})
        with Session() as session:
            proposal = self.account.get_proposal(session)
            new_sus = getattr(proposal, settings.test_cluster)

        self.assertEqual(self.num_proposal_sus - sus_to_subtract, new_sus)

    def test_error_on_bad_cluster_name(self) -> None:
        """Test a ``ValueError`` is raised if the cluster name is not defined in application settings"""

        fake_cluster_name = 'fake_cluster'
        with self.assertRaisesRegex(ValueError, f'Cluster {fake_cluster_name} is not defined*'):
            self.account.subtract(**{fake_cluster_name: 1000})

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.subtract(**{settings.test_cluster: -1})

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` error is raised when account has no proposal"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingProposalError):
            self.account.subtract(**{settings.test_cluster: -1})


class OverwriteSus(ProposalSetup, TestCase):
    """Test the modification of allocated sus via the ``set_cluster_allocation`` method"""

    def test_sus_are_modified(self) -> None:
        """Test sus are overwritten in the proposal"""

        with Session() as session:
            old_proposal = self.account.get_proposal(session)

        self.account.overwrite(**{settings.test_cluster: 12345})
        with Session() as session:
            new_proposal = self.account.get_proposal(session)

        # Check service units are overwritten but dates are not
        self.assertEqual(12345, getattr(new_proposal, settings.test_cluster))
        self.assertEqual(old_proposal.start_date, new_proposal.start_date)
        self.assertEqual(old_proposal.end_date, new_proposal.end_date)

    def test_dates_are_modified(self) -> None:
        """Test start and end dates are overwritten in the proposal"""

        with Session() as session:
            old_proposal = self.account.get_proposal(session)

        new_start_date = old_proposal.start_date + timedelta(days=5)
        new_end_date = old_proposal.end_date + timedelta(days=10)
        self.account.overwrite(start_date=new_start_date, end_date=new_end_date)

        with Session() as session:
            new_proposal = self.account.get_proposal(session)

        # Check service units are overwritten but dates are not
        self.assertEqual(getattr(old_proposal, settings.test_cluster), getattr(new_proposal, settings.test_cluster))
        self.assertEqual(new_start_date, new_proposal.start_date)
        self.assertEqual(new_end_date, new_proposal.end_date)

    def test_error_on_bad_cluster_name(self) -> None:
        """Test a ``ValueError`` is raised if the cluster name is not defined in application settings"""

        fake_cluster_name = 'fake_cluster'
        with self.assertRaisesRegex(ValueError, f'Cluster {fake_cluster_name} is not defined*'):
            self.account.overwrite(**{fake_cluster_name: 1000})

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.overwrite(**{settings.test_cluster: -1})

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` error is raised when account has no proposal"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingProposalError):
            self.account.overwrite(**{settings.test_cluster: 1})
