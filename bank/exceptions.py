"""The ``exceptions`` module defines custom exceptions raised by the
parent application.

API Reference
-------------
"""


class CmdError(Exception):
    """Raised when a piped command writes to STDERR in the underlying shell"""


class MissingProposalError(Exception):
    """Raised when an account is missing a proposal in the bank database"""
