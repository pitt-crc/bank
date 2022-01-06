from unittest import TestCase
from unittest.mock import patch

from bank import settings
from bank.dao import AdminServices
from tests.dao._utils import InvestorSetup


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


class Renewal(InvestorSetup, TestCase):
    """Tests for the renewal of investment accounts"""

    def test_proposal_is_archived(self) -> None:
        self.fail()

    def test_new_proposal_is_created(self) -> None:
        self.fail()

    def test_investments_are_archived(self) -> None:
        self.fail()

    def test_investments_are_rolled_over(self) -> None:
        self.fail()
