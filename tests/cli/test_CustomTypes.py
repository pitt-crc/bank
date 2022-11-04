"""Tests for the ``ArgumentTypes`` class"""

from argparse import ArgumentTypeError
from unittest import TestCase

from bank.cli import ArgumentTypes


class NonNegativeIntCasting(TestCase):
    """Tests for type casting via the ``non_negative_int`` method"""

    def test_blank_string_error(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a blank string"""

        with self.assertRaises(ArgumentTypeError):
            ArgumentTypes.non_negative_int('')

    def test_negative_int(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a negative integer"""

        with self.assertRaises(ArgumentTypeError):
            ArgumentTypes.non_negative_int('-1')

    def test_negative_float(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a negative float"""

        with self.assertRaises(ArgumentTypeError):
            ArgumentTypes.non_negative_int('-1.8')

    def test_positive_int(self) -> None:
        """Test integer values are returned as integers"""

        self.assertEqual(1, ArgumentTypes.non_negative_int('1'))
        self.assertEqual(234, ArgumentTypes.non_negative_int('234'))

    def test_positive_float(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a positive float"""

        with self.assertRaises(ArgumentTypeError):
            ArgumentTypes.non_negative_int('1.8')

    def test_zero(self) -> None:
        """Test the string ``"0"`` is returned as the integer ``0``"""
        self.assertEqual(0, ArgumentTypes.non_negative_int('0'))
