"""Extends the default functionality of SQLAlchemy tables

API Reference
-------------
"""

from enum import Enum


class ProposalEnum(Enum):
    Proposal = 0
    Class = 1


class Validators:
    """Methods for validating column values before interacting with the database"""

    def validate_service_units(self, key: str, value: int) -> int:
        """Verify the given value is a non-negative integer

        Raises:
            ValueError: If the given value does not match required criteria
        """

        if value < 0:
            raise ValueError(f'Invalid value for column {key} - Service units must be a non-negative integer.')

        return value

    def validate_percent_notified(self, key: str, value: int) -> int:
        """Verify the given value is between 0 and 100

        Raises:
            ValueError: If the given value does not match required criteria
        """

        if 0 <= value <= 100:
            return value

        raise ValueError(f'Value for {key} must be between 0 and 100 (get {value}).')
