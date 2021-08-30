"""Custom exceptions raised by the ``bank`` application."""


class CmdError(Exception):
    """Raised when a piped command writes to STDERR in the underlying shell"""


class MissingProposalError(Exception):
    """Raised when an account is missing a proposal in the bank database"""
