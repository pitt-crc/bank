from datetime import date, timedelta
from unittest import TestCase
from unittest.mock import patch

import time_machine

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


class Renewal(AdminSetup, TestCase):
    """Tests for the renewal of investment accounts"""

    def setUp(self) -> None:
        super().setUp()
        with time_machine.travel(TODAY + timedelta(days=366)):
            self.account.renew(reset_usage=False)

    def test_proposal_is_archived(self, *args) -> None:
        self.assertIsNone(self.session.query(orm.Proposal).filter(orm.Proposal.id == self.proposal_id).first())
        self.assertTrue(self.session.query(orm.ProposalArchive).filter(orm.Proposal.id == self.proposal_id).first())

    def test_new_proposal_is_created(self, *args) -> None:
        # Compare the id of the current proposal with the id of the original proposal
        new_proposal_id = self.account._get_proposal(self.session).id
        self.assertNotEqual(new_proposal_id, self.proposal_id)

    def test_investments_are_archived(self, *args) -> None:
        investment = self.session.query(orm.InvestorArchive).filter(orm.InvestorArchive.id == self.inv_id[0])
        self.assertTrue(investment, 'No investment found in archive table')

    def test_investments_are_rolled_over(self, *args) -> None:
        current_investment = self.account._get_investment(self.session, self.inv_id[-1])
        self.assertEqual(self.num_inv_sus * settings.inv_rollover_fraction, current_investment.rollover_sus)
