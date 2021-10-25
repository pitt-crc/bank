from unittest import TestCase
from unittest.mock import patch

from bank.dao import Account
from bank.exceptions import MissingProposalError, ProposalExistsError
from bank.orm import Session, Proposal
from bank.settings import app_settings


class GenericSetup:
    """Reusable setup mixin for configuring a unittest class"""

    def setUp(self) -> None:
        """Delete any proposals that may already exist for the test account"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == app_settings.test_account).delete()
            session.commit()

        self.account = Account(app_settings.test_account)
        self.account.create_proposal()


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


class AddAllocationSus(GenericSetup, TestCase):
    """Tests for the addition of sus via the ``add_allocation_sus`` method"""

    def test_sus_are_added(self) -> None:
        """Test sus from kwargs are set in the proposal"""

        cluster_name = app_settings.clusters[0]
        self.account.add_allocation_sus(**{cluster_name: 1000})
        recovered_sus = self.account.get_proposal_info()[cluster_name]
        self.assertEqual(1000, recovered_sus)

    def test_error_on_bad_cluster_name(self) -> None:
        """Test a ``ValueError`` is raised if the cluster name is not defined in application settings"""

        fake_cluster_name = 'fake_cluster'
        with self.assertRaisesRegex(ValueError, f'Cluster {fake_cluster_name} is not defined in application settings.'):
            self.account.add_allocation_sus(**{fake_cluster_name: 1000})


class SetClusterAllocation(GenericSetup, TestCase):
    """Test the modification of allocated sus via the ``set_cluster_allocation`` method"""

    def test_sus_are_added(self) -> None:
        """Test sus from kwargs are set in the proposal"""

        cluster_name = app_settings.clusters[0]
        self.account.overwrite_allocation_sus(**{cluster_name: 1000})
        recovered_sus = self.account.get_proposal_info()[cluster_name]
        self.assertEqual(1000, recovered_sus)

    def test_error_on_bad_cluster_name(self) -> None:
        """Test a ``ValueError`` is raised if the cluster name is not defined in application settings"""

        fake_cluster_name = 'fake_cluster'
        with self.assertRaisesRegex(ValueError, f'Cluster {fake_cluster_name} is not defined in application settings.'):
            self.account.overwrite_allocation_sus(**{fake_cluster_name: 1000})


class PrintAllocationInfo(GenericSetup, TestCase):

    @patch('builtins.print')
    def test_printed_text_is_not_empty(self, mocked_print) -> None:
        Account(app_settings.test_account).print_usage_info()
        printed_text = '\n'.join(c.args[0] for c in mocked_print.mock_calls)
        self.assertTrue(printed_text)


class PrintUsageInfo(GenericSetup, TestCase):

    @patch('builtins.print')
    def test_printed_text_is_not_empty(self, mocked_print) -> None:
        Account(app_settings.test_account).print_usage_info()
        printed_text = '\n'.join(c.args[0] for c in mocked_print.mock_calls)
        self.assertTrue(printed_text)