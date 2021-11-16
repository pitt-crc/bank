from unittest import TestCase

from bank.dao import Account
from bank.exceptions import MissingProposalError


class CalculatePercentage(TestCase):
    """Tests for the calculation of percentages"""

    def test_divide_by_zero(self) -> None:
        """Test dividing by zero returns zero"""

        self.assertEqual(0, Account._calculate_percentage(100, 0))

    def test_divide_by_positive(self) -> None:
        """Test dividing by a positive number gives a percentage"""

        self.assertEqual(50, Account._calculate_percentage(1, 2))


class PrintAllocationInfo(TestCase):
    """Tests for the ``print_allocation_info`` method"""

    def test_error_on_missing_proposal(self) -> None:
        """Test a ``MissingProposalError`` error is raised if the account does not exist"""

        with self.assertRaises(MissingProposalError):
            Account('fake_account_name').print_allocation_info()
