from datetime import timedelta
from unittest import TestCase
from unittest.mock import patch

import time_machine

from bank import orm
from bank import settings
from bank.dao import AdminServices
from bank.system.slurm import SlurmAccount
from tests.dao._utils import AdminSetup


class CalculatePercentage(TestCase):
    """Tests for the calculation of percentages"""

    def test_divide_by_zero(self) -> None:
        """Test dividing by zero returns zero"""

        self.assertEqual(0, AdminServices._calculate_percentage(100, 0))

    def test_divide_by_positive(self) -> None:
        """Test dividing by a positive number gives a percentage"""

        self.assertEqual(50, AdminServices._calculate_percentage(1, 2))


class PrintInfo(TestCase):

    @patch('builtins.print')
    def test_output_not_empty(self, mocked_print):
        AdminServices(settings.test_account).print_info()
        self.assertTrue(mocked_print.mock_calls)


class Renewal(AdminSetup, TestCase):
    """Tests for the renewal of investment accounts"""

    @patch.object(SlurmAccount, "get_cluster_usage", return_value=0)
    def setUp(self, *args) -> None:
        super().setUp()

        # Fast-forward in time to after the end of the first investment
        investments = self.account._get_investment(self.session)
        end_of_first_inv = investments[0].end_date
        with time_machine.travel(end_of_first_inv + timedelta(days=1)):
            self.account.renew(reset_usage=False)

    def test_proposal_is_archived(self) -> None:
        """Test the original user proposal is archived"""

        original_proposal = self.session.query(orm.Proposal).filter(orm.Proposal.id == self.proposal_id).first()
        self.assertIsNone(original_proposal, 'Original proposal was not deleted')

        archived_proposal = self.session.query(orm.ProposalArchive).filter(orm.ProposalArchive.id == self.proposal_id).first()
        self.assertTrue(archived_proposal, 'Copy of proposal was not created in the archive')

    def test_new_proposal_is_created(self) -> None:
        """Test a new user proposal is created"""

        # Compare the id of the current proposal with the id of the original proposal
        new_proposal = self.account._get_proposal(self.session)
        self.assertNotEqual(new_proposal.id, self.proposal_id, 'New proposal has same ID as the old one')
        self.assertEqual(
            getattr(new_proposal, settings.test_cluster), self.num_proposal_sus,
            'New proposal does not have same service units as the old one')

    def test_investments_are_archived(self) -> None:
        """Test expired investments are archived"""

        archived_investment = self.session.query(orm.InvestorArchive).filter(orm.InvestorArchive.id == self.inv_id[0])
        self.assertTrue(archived_investment, 'No investment found in archive table')

        remaining_investments = self.account._get_investment(self.session)
        self.assertEqual(len(self.inv_id) - 1, len(remaining_investments))

    def test_investments_are_rolled_over(self) -> None:
        """Test unused investment service units are rolled over"""

        current_investment = self.account._get_investment(self.session)[0]
        self.assertEqual(self.num_inv_sus * settings.inv_rollover_fraction, current_investment.rollover_sus)


@patch('smtplib.SMTP')
class LockIfExpired(AdminSetup, TestCase):
    """Test for emails sent when locking accounts"""

    def test_email_sent_for_expired(self, mock_smtp) -> None:
        proposal = self.account._get_proposal(self.session)
        with time_machine.travel(proposal.end_date):
            self.account._lock_if_expired()

    def test_email_sent_for_warning_day(self, mock_smtp) -> None:
        proposal = self.account._get_proposal(self.session)
        with patch.object(settings, "warning_days", (10,)), time_machine.travel(proposal.end_date - timedelta(days=10)):
            self.account._lock_if_expired()

    def test_email_sent_for_percent_notified(self, mock_smtp) -> None:
        proposal = self.account._get_proposal(self.session)
        with time_machine.travel(proposal.end_date):
            self.account._lock_if_expired()
