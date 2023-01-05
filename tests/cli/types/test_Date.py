"""Tests for the ``ArgumentTypes`` class"""

import string
from argparse import ArgumentTypeError
from datetime import date
from unittest import TestCase

from bank import settings
from bank.cli.types import Date


class BlankArgument(TestCase):
    """Test type casting behavior for blank strings"""

    def test_blank_string_error(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for a blank string"""

        with self.assertRaises(ArgumentTypeError):
            Date('')

    def test_whitespace_string_error(self) -> None:
        """Test ``ArgumentTypeError`` is raised when string is whitespace"""

        for char in string.whitespace:
            with self.assertRaises(ArgumentTypeError):
                Date(char)


class DateCasting(TestCase):
    """Test type casting against various date formats"""

    def test_invalid_value_err(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for strings not representing valid dates"""

        with self.assertRaises(ArgumentTypeError):
            Date('this is not a date')

    def test_invalid_format_err(self) -> None:
        """Test an ``ArgumentTypeError`` is raised for valid dates using the wrong string format"""

        test_date = date(2000, 11, 12)
        test_format = '%b %d %Y'

        self.assertNotEqual(test_format, settings.date_format)
        with self.assertRaises(ArgumentTypeError):
            Date(test_date.strftime(test_format))

    def test_valid_format(self) -> None:
        """Test date strings matching the format in application settings are returned as date objects"""

        test_date = date(2000, 11, 12)
        test_date_str = test_date.strftime(settings.date_format)
        self.assertEqual(test_date, Date(test_date_str))
