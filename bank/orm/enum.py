"""Definitions of enumerated data types used in the database"""

from __future__ import annotations

from enum import Enum


class ProposalType(Enum):
    PROPOSAL = 0
    CLASS = 1
    INVESTOR = 2
