"""Definitions of enumerated data types used in the database."""

from __future__ import annotations

from enum import Enum


class ProposalType(Enum):
    """The type of proposal assigned to an account"""

    Proposal = 0
    Class = 1
    Investor = 2
