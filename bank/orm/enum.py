"""Enumerated data types used to represent values in the application database.

API Reference
-------------
"""

from __future__ import annotations

from enum import Enum


class BaseEnum(Enum):
    """Extends the behavior of the builtin ``Enum`` class for easier instance construction"""

    @classmethod
    def from_string(cls, string: str) -> BaseEnum:
        """Return an instance of the parent class corresponding to the given type

        Args:
            string: The name of the Enum value as a string

        Returns:
            An instance of the parent Enum class
        """

        try:
            return cls[string]

        except KeyError:
            raise ValueError(f'Invalid Enum type: {string}')

    def __str__(self) -> str:
        return self.name


class ProposalEnum(BaseEnum):
    """Represents different classifications of user proposals"""

    Unknown = 99
    Proposal = 1
    Class = 2
