"""Extends the default functionality of SQLAlchemy tables

API Reference
-------------
"""

import enum


class ProposalEnum(enum.Enum):
    Proposal = 0
    Class = 1

    def __str__(self):
        return self.name

    @classmethod
    def from_string(cls, s):
        try:
            return cls[s]

        except KeyError:
            raise ValueError(f'Invalid ProposalEnum type: {s}')


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
