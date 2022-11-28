"""The ``exceptions`` module defines custom exceptions raised by the parent application.

The parent application interfaces with several external systems.
This can make tracebacks and error messages confusing at first glance.
For the sake of clarity, a liberal approach is taken when defining
custom exceptions.

API Reference
-------------
"""


class CmdError(Exception):
    """Raised when a piped command writes to STDERR in the underlying shell."""


class SlurmAccountNotFoundError(Exception):
    """Raised when a Slurm user account does not exist."""


class SlurmClusterNotFoundError(Exception):
    """Raised when a Slurm cluster does not exist."""


class FormattingError(Exception):
    """Raised when incorrectly formatting angit a email template."""


class MissingProposalError(Exception):
    """Raised when an account is missing a proposal in the bank database."""


class ProposalExistsError(Exception):
    """Raised when trying to create a proposal that already exists."""


class MissingInvestmentError(Exception):
    """Raised when an account is missing an investment in the bank database."""


class InvestmentExistsError(Exception):
    """Raised when trying to create an investment that already exists."""
