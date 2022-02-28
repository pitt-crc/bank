"""The ``exceptions`` module defines custom exceptions raised by the parent application.

The parent application interfaces with several external systems.
This can make tracebacks and error messages confusing at first glance.
For the sake of clarity, we take a liberal approach to the
definition of custom exceptions.

API Reference
-------------
"""


class CmdError(Exception):
    """Raised when a piped command writes to STDERR in the underlying shell."""


class MissingProposalError(Exception):
    """Raised when an account is missing a proposal in the bank database."""


class MissingInvestmentError(Exception):
    """Raised when an account is missing an investment in the bank database."""


class ProposalExistsError(Exception):
    """Raised when trying to create a proposal that already exists"""


class TableOverwriteError(Exception):
    """Raised when database entries are about to be overwritten"""


class SlurmAccountNotFoundError(Exception):
    """Raised when a Slurm user account does not exist"""


class SlurmAccountExistsError(Exception):
    """Raised when a Slurm user account already exists"""


class LdapUserNotFound(Exception):
    """Raised when an LDAP user is referenced that does not exist"""


class LDAPGroupNotFound(Exception):
    """Raised when an LDAP group is referenced that does not exist"""


class MissingFieldsError(Exception):
    """Raised when trying to send an incomplete email template"""
