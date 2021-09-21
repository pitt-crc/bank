from __future__ import annotations

from enum import Enum


class ProposalType(Enum):
    Proposal = 0
    Class = 1
    Investor = 2

    @classmethod
    def from_string(cls, name: str) -> ProposalType:
        try:
            return cls(getattr(cls, name))

        except AttributeError:
            raise ValueError(f'Invalid proposal type: `{name}`.')
