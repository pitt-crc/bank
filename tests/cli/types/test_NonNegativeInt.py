"""Tests for the ``NonNegativeInt`` class"""

import string
from argparse import ArgumentTypeError
from unittest import TestCase

from bank.cli.types import NonNegativeInt


class BlankArgument(TestCase):
    """Test type casting behavior for blank strings"""

    def test_empty_string_error(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a blank string"""

        with self.assertRaises(ArgumentTypeError):
            NonNegativeInt('')

    def test_whitespace_string_error(self) -> None:
        """Test ``ArgumentTypeError`` is raised when string is whitespace"""

        for char in string.whitespace:
            with self.assertRaises(ArgumentTypeError):
                NonNegativeInt(char)


class IntegerCasting(TestCase):
    """Test type casting of numerical arguments"""

    def test_negative_int(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a negative integer"""

        with self.assertRaises(ArgumentTypeError):
            NonNegativeInt('-1')

    def test_negative_float(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a negative float"""

        with self.assertRaises(ArgumentTypeError):
            NonNegativeInt('-1.8')

    def test_positive_int(self) -> None:
        """Test integer values are returned as integers"""

        self.assertEqual(1, NonNegativeInt('1'))
        self.assertEqual(234, NonNegativeInt('234'))

    def test_positive_float(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a positive float"""

        with self.assertRaises(ArgumentTypeError):
            NonNegativeInt('1.8')

    def test_zero(self) -> None:
        """Test the string ``"0"`` is returned as the integer ``0``"""

        self.assertEqual(0, NonNegativeInt('0'))
