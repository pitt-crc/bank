from unittest import TestCase

from bank import settings
from bank.dao import ProposalServices
from bank.exceptions import MissingProposalError, ProposalExistsError
from bank.orm import Session, Proposal
from tests.dao._utils import ProposalSetup


class CreateProposal(TestCase):
    """Tests for the creation of proposals via the ``create_proposal`` method"""

    def setUp(self) -> None:
        """Delete any proposals that may already exist for the test account"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.commit()

        self.account = ProposalServices(settings.test_account)

    def test_proposal_is_created(self) -> None:
        """Test a proposal is created after the function call"""

        # Avoid false positives by checking the proposal doesn't already exist
        with self.assertRaises(MissingProposalError):
            self.account._get_proposal_info()

        self.account.create_proposal()
        self.assertTrue(self.account._get_proposal_info())

    def test_default_sus_are_zero(self) -> None:
        """Test proposals are created with zero service units by default"""

        self.account.create_proposal()
        proposal_info = self.account._get_proposal_info()
        for cluster in settings.clusters:
            self.assertEqual(0, proposal_info[cluster])

    def test_non_default_sus_are_set(self) -> None:
        """Tests proposal are assigned the number of sus specified by kwargs"""

        self.account.create_proposal(**{c: 1000 for c in settings.clusters})
        proposal_info = self.account._get_proposal_info()

        for cluster in settings.clusters:
            self.assertEqual(1000, proposal_info[cluster])

    def test_error_if_already_exists(self) -> None:
        """Test a ``ProposalExistsError`` error is raised if the proposal already exists"""

        self.account.create_proposal()
        with self.assertRaises(ProposalExistsError):
            self.account.create_proposal()

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.create_proposal(**{settings.test_cluster: -1})


class AddAllocationSus(ProposalSetup, TestCase):
    """Tests for the addition of sus via the ``add`` method"""

    def test_sus_are_added(self) -> None:
        """Test SUs from kwargs are set in the proposal"""

        cluster_name = settings.test_cluster
        for sus_to_add in (0, 1000):
            original_sus = self.account._get_proposal_info()[cluster_name]
            self.account.add(**{cluster_name: sus_to_add})
            new_sus = self.account._get_proposal_info()[cluster_name]
            self.assertEqual(original_sus + sus_to_add, new_sus, f'SUs not added (tried to add {sus_to_add})')

    def test_error_on_bad_cluster_name(self) -> None:
        """Test a ``ValueError`` is raised if the cluster name is not defined in application settings"""

        fake_cluster_name = 'fake_cluster'
        with self.assertRaisesRegex(ValueError, f'Cluster {fake_cluster_name} is not defined in application settings.'):
            self.account.add(**{fake_cluster_name: 1000})

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.add(**{settings.test_cluster: -1})

    def test_error_on_missing_proposal(self) -> None:
        """Test an error is raised when account has no proposal"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingProposalError):
            self.account.add(**{settings.test_cluster: -1})


class SetClusterAllocation(ProposalSetup, TestCase):
    """Test the modification of allocated sus via the ``set_cluster_allocation`` method"""

    def test_sus_are_modified(self) -> None:
        """Test sus from kwargs are set in the proposal"""

        self.account.overwrite(**{settings.test_cluster: 1000})
        recovered_sus = self.account._get_proposal_info()[settings.test_cluster]
        self.assertEqual(1000, recovered_sus)

    def test_error_on_bad_cluster_name(self) -> None:
        """Test a ``ValueError`` is raised if the cluster name is not defined in application settings"""

        fake_cluster_name = 'fake_cluster'
        with self.assertRaisesRegex(ValueError, f'Cluster {fake_cluster_name} is not defined in application settings.'):
            self.account.overwrite(**{fake_cluster_name: 1000})

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.overwrite(**{settings.test_cluster: -1})

    def test_error_on_missing_proposal(self) -> None:
        """Test an error is raised when account has no proposal"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.commit()

        with self.assertRaises(MissingProposalError):
            self.account.overwrite(**{settings.test_cluster: 1})
