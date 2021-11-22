"""Definitions of enumerated data types used to represent database columns"""

from __future__ import annotations

from enum import Enum


class ProposalType(Enum):
    PROPOSAL = 0
    CLASS = 1
    INVESTOR = 2

    @classmethod
    def get(cls, name):
        try:
            return cls[name]

        except KeyError:
            cls._missing_(name)
