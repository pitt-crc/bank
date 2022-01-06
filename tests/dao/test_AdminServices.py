from datetime import date, timedelta
from unittest import TestCase
from unittest.mock import patch

from bank import orm
from bank import settings
from bank.dao import AdminServices
from tests.dao._utils import AdminSetup

TODAY = date.today()


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


# We patch the slurm commands because they require root permissions
# Patching the datetime allows us to pretend we are in the future when
# proposals/investments have expired
@patch('datetime.date')
@patch('bank.system.SlurmAccount.reset_raw_usage')
@patch('bank.system.SlurmAccount.set_locked_state')
class Renewal(AdminSetup, TestCase):
    """Tests for the renewal of investment accounts"""

    def test_proposal_is_archived(self, mock_date, *args) -> None:
        mock_date.today.return_value = TODAY + timedelta(days=366)
        self.account.renew()

        self.assertIsNone(self.session.query(orm.Proposal).filter(id=self.proposal_id).first())
        self.assertTrue(self.session.query(orm.ProposalArchive).filter(id=self.proposal_id).first())

    def test_new_proposal_is_created(self, mock_date, *args) -> None:
        mock_date.today.return_value = TODAY + timedelta(days=366)
        self.account.renew()

        # Compare the id of the current proposal with the id of the original proposal
        new_proposal_id = self.account._get_proposal(self.session).id
        self.assertNotEqual(new_proposal_id, self.proposal_id)

    def test_investments_are_archived(self, mock_date, *args) -> None:
        mock_date.today.return_value = TODAY + timedelta(days=366)
        self.account.renew()

        investment = self.session.query(orm.InvestorArchive).filter(id=self.inv_id[0])
        self.assertTrue(investment, 'No investment found in archive table')

    def test_investments_are_rolled_over(self, mock_date, *args) -> None:
        mock_date.today.return_value = TODAY + timedelta(days=366)
        self.account.renew()

        current_investment = self.account._get_investment(self.session, self.inv_id[1])
        self.assertEqual(self.num_inv_sus * (1 + settings.inv_rollover_fraction), current_investment.current_sus)
