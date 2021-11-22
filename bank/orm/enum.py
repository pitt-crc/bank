"""Definitions of enumerated data types used to represent database columns"""

from __future__ import annotations

from enum import Enum


class ProposalType(Enum):
    PROPOSAL = 0
    CLASS = 1
    INVESTOR = 2

    @classmethod
    def get(cls, name):
        """Return the enum instance that is equivalent to the non-enumerated value

        Args:
            The name of the value to return an enumerated instance for
        """

        try:
            return cls[name]

        except KeyError:
            cls(name)
