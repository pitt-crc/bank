"""The ``exceptions`` module defines custom exceptions raised by the parent application.

Summary of Custom Exceptions
----------------------------

.. autosummary::
   :nosignatures:

   bank.exceptions.CmdError
   bank.exceptions.MissingProposalError
   bank.exceptions.TableOverwriteError
"""


class CmdError(Exception):
    """Raised when a piped command writes to STDERR in the underlying shell."""


class MissingProposalError(Exception):
    """Raised when an account is missing a proposal in the bank database."""


class TableOverwriteError(Exception):
    """Raised when database entries are about to be overwritten."""
