"""The ``exceptions`` module defines custom exceptions raised by the parent application.

Summary of Exceptions
---------------------

.. autosummary::
   :nosignatures:

   bank.exceptions.CmdError
   bank.exceptions.MissingProposalError
   bank.exceptions.TableOverwriteError
   bank.exceptions.NoSuchAccountError
"""


class CmdError(Exception):
    """Raised when a piped command writes to STDERR in the underlying shell."""


class MissingProposalError(Exception):
    """Raised when an account is missing a proposal in the bank database."""


class TableOverwriteError(Exception):
    """Raised when database entries are about to be overwritten"""


class NoSuchAccountError(Exception):
    """Raised when a Slurm user account does not exist"""
