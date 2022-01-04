from unittest import TestCase
from unittest.mock import patch

from bank import settings
from bank.dao import AdminServices


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
