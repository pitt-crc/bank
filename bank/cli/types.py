"""The ``cli.types`` module defines factory classes for casting parsed
commandline arguments (strings) into other useful object types.
"""

from argparse import ArgumentTypeError
from datetime import date, datetime

from bank import settings


class Date:
    """Factory class for creating ``date`` instances from strings

    Date information is expected to follow the string format
    specified in application settings.
    """

    def __new__(cls, val: str, /) -> date:
        """Cast a string to a ``date`` object

        Args:
            val: The string value to cast

        Returns:
            The passed value as ``date`` instance

        Raises:
            ArgumentTypeError: If the value cannot be parsed as a date
        """

        try:
            return datetime.strptime(val, settings.date_format).date()

        except Exception as exception:
            raise ArgumentTypeError(f'Could not parse the given date: {val}') from exception


class NonNegativeInt:
    """Factory class for creating ``int`` instances from strings"""

    def __new__(cls, val: str, /) -> int:
        """Cast a string to a non-negative ``int`` object

        Args:
            val: The string value to cast

        Returns:
            The passed value as an ``int`` instance

        Raises:
            ArgumentTypeError: If the integer value is less than zero
        """

        try:
            number = int(val)

        except Exception as exception:
            raise ArgumentTypeError(str(exception)) from exception

        if number < 0:
            raise ArgumentTypeError(f'Argument must be a non-negative integer: {val}')

        return number
