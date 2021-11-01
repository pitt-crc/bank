from datetime import date, timedelta
from unittest import TestCase, skipIf

from bank.orm import Proposal
from bank.settings import app_settings
from bank.system import SlurmAccount
from tests.orm import base_tests


class HasDynamicColumns(TestCase, base_tests.HasDynamicColumns):
    """Test for dynamically added columns based on administered cluster names"""

    db_table_class = Proposal


class ServiceUnitsValidation(TestCase, base_tests.ServiceUnitsValidation):
    """Tests for the validation of the service units"""

    db_table_class = Proposal
    columns_to_test = app_settings.clusters


class PercentNotifiedValidation(TestCase):
    """Tests for the validation of the ``percent_notified``` column"""

    def test_percent_notified_out_of_range(self) -> None:
        """Test for a ``ValueError`` when ``percent_notified`` is not between 0 and 100"""

        with self.assertRaises(ValueError):
            Proposal(percent_notified=-1)

        with self.assertRaises(ValueError):
            Proposal(percent_notified=101)

        Proposal(percent_notified=0)
        Proposal(percent_notified=100)

    def test_percent_notified_in_range(self) -> None:
        """Test no error is raised when ``percent_notified`` is not between 0 and 100"""

        proposal = Proposal(percent_notified=50)
        self.assertEqual(50, proposal.percent_notified)


@skipIf(not SlurmAccount.check_slurm_installed(), 'Slurm is not installed on this machine')
class ToArchiveObject(TestCase):
    """Test the casting of a ``Proposal`` object to a ``ProposalArchive`` object"""

    def setUp(self) -> None:
        """Create a ``Proposal`` instance for testing"""

        self.proposal = Proposal(
            account_name=app_settings.test_account,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            percent_notified=10,
            proposal_type=1
        )

        for cluster in app_settings.clusters:
            setattr(self.proposal, cluster, 10)

        self.archive_obj = self.proposal.to_archive_object()

    def test_column_values_match_original_object(self) -> None:
        """Test the attributes of the returned object match the original proposal"""

        col_names = ('id', 'account_name', 'start_date', 'end_date', 'proposal_type', app_settings.test_cluster)
        for c in col_names:
            self.assertEqual(getattr(self.proposal, c), getattr(self.archive_obj, c))

    def test_account_usage_matches_slurm_output(self) -> None:
        """Test the account usage agrees with the output of the slurm utility"""

        slurm_account = SlurmAccount(app_settings.test_account)
        self.assertEqual(
            slurm_account.get_cluster_usage(app_settings.test_cluster),
            getattr(self.archive_obj, f'{app_settings.test_cluster}_usage')
        )
