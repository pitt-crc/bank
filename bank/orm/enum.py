from __future__ import annotations

from enum import Enum


class ProposalType(Enum):
    Proposal_Type = 0
    Class_Type = 1
    Investor_Type = 2

    @classmethod
    def from_string(cls, name: str) -> ProposalType:
        try:
            return cls(getattr(cls, name))

        except AttributeError:
            raise from ValueError(f'Invalid proposal type: `{name}`.')
