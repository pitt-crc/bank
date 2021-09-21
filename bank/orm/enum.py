from __future__ import annotations

from enum import Enum


class ProposalType(Enum):
    proposal = 0
    classes = 1
    investor = 2

    @classmethod
    def from_string(cls, name: str) -> ProposalType:
        try:
            return cls(getattr(cls, name))

        except AttributeError:
            raise ValueError(f'Invalid proposal type: `{name}`.')
