"""Definitions of enumerated data types used to represent database columns"""

from __future__ import annotations

from enum import Enum
from typing import List


class ProposalType(Enum):
    PROPOSAL = 0
    CLASS = 1
    INVESTOR = 2

    @property
    def valid_values(self) -> List[str]:
        """Values represented as enumerated types by the parent class"""

        return list(ProposalType.__members__.keys())

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
