"""Enumerated data types used to represent values in the application database.

API Reference
-------------
"""

from __future__ import annotations

from enum import Enum


class BaseEnum(Enum):
    """Extends behavior of the base ``Enum`` class for easier casting"""

    @classmethod
    def from_string(cls, string: str) -> ProposalEnum:
        """Return an instance of the parent class corresponding to a proposal type"""

        try:
            return cls[string]

        except KeyError:
            raise ValueError(f'Invalid ProposalEnum type: {string}')

    def __str__(self) -> str:
        return self.name


class ProposalEnum(BaseEnum):
    """Represents different classifications of user proposals"""

    Unknown = 99
    Proposal = 1
    Class = 2
