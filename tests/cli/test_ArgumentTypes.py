"""Tests for the ``ArgumentTypes`` class"""

from argparse import ArgumentTypeError
from datetime import date
import string
from unittest import TestCase

from bank import settings
from bank.cli import ArgumentTypes


class DateCasting(TestCase):
    """Test type casting via the ``date`` method"""

    def test_blank_string_error(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a blank string"""

        with self.assertRaises(ArgumentTypeError):
            ArgumentTypes.date('')

    def test_whitespace_string_error(self) -> None:
        """Test ``ArgumentTypeError`` is raised when string is whitespace"""

        for char in string.whitespace:
            with self.assertRaises(ArgumentTypeError):
                ArgumentTypes.date(char)

    def test_invalid_value_err(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for strings not representing valid dates"""

        with self.assertRaises(ArgumentTypeError):
            ArgumentTypes.date('this is not a date')

    def test_invalid_format_err(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for valid dates using the wrong string format"""

        test_date = date(2000, 11, 12)
        test_format = '%b %d %Y'

        self.assertNotEqual(test_format, settings.date_format)
        with self.assertRaises(ArgumentTypeError):
            ArgumentTypes.date(test_date.strftime(test_format))

    def test_valid_format(self) -> None:
        """Test date strings matching the format in application settings are returned as date objects"""

        test_date = date(2000, 11, 12)
        test_date_str = test_date.strftime(settings.date_format)
        self.assertEqual(test_date, ArgumentTypes.date(test_date_str))


class NonNegativeIntCasting(TestCase):
    """Tests for type casting via the ``non_negative_int`` method"""

    def test_blank_string_error(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a blank string"""

        with self.assertRaises(ArgumentTypeError):
            ArgumentTypes.non_negative_int('')

    def test_whitespace_string_error(self) -> None:
        """Test ``ArgumentTypeError`` is raised when string is whitespace"""

        for char in string.whitespace:
            with self.assertRaises(ArgumentTypeError):
                ArgumentTypes.non_negative_int(char)

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
