"""The ``exceptions`` module defines custom exceptions raised by the parent application.

Summary of Exceptions
---------------------

.. autosummary::
   :nosignatures:

   bank.exceptions.CmdError
   bank.exceptions.MissingProposalError
   bank.exceptions.ProposalExistsError
   bank.exceptions.TableOverwriteError
   bank.exceptions.NoSuchAccountError
"""


class CmdError(Exception):
    """Raised when a piped command writes to STDERR in the underlying sohell."""


class MissingProposalError(Exception):
    """Raised when an account is missing a proposal in the bank database."""


class MissingInvestmentError(Exception):
    """Raised when an account is missing an investment in the bank database."""


class ProposalExistsError(Exception):
    """Raised when trying to create a proposal that already exists"""


class TableOverwriteError(Exception):
    """Raised when database entries are about to be overwritten"""


class NoSuchAccountError(Exception):
    """Raised when a Slurm user account does not exist"""
