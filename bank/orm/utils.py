"""General utilities and data types used for interacting with the application database.

API Reference
-------------
"""

from __future__ import annotations

import enum


class ProposalEnum(enum.Enum):
    """Enum type for different user proposals"""

    Unknown = 99
    Proposal = 1
    Class = 2

    @classmethod
    def from_string(cls, string: str) -> ProposalEnum:
        """Return an instance of the parent class corresponding to a proposal type"""

        try:
            return cls[string]

        except KeyError:
            raise ValueError(f'Invalid ProposalEnum type: {string}')

    def __str__(self) -> str:
        return self.name


class Validators:
    """Methods for validating column values before interacting with the database"""

    def _validate_service_units(self, key: str, value: int) -> int:
        """Verify the given value is a non-negative integer

        Args:
            key: Name of the column data is being entered into
            value: The value to test

        Raises:
            ValueError: If the given value does not match required criteria
        """

        if value < 0:
            raise ValueError(f'Invalid value for column {key} - Service units must be a non-negative integer.')

        return value

    def _validate_percent_notified(self, key: str, value: int) -> int:
        """Verify the given value is between 0 and 100 (inclusive)

        Args:
            key: Name of the column data is being entered into
            value: The value to test

        Raises:
            ValueError: If the given value does not match required criteria
        """

        if 0 <= value <= 100:
            return value

        raise ValueError(f'Value for {key} must be between 0 and 100 (get {value}).')
