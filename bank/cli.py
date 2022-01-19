"""The ``cli`` module defines the command line interface for the parent
application. This module is effectively a wrapper around existing functionality
defined in the ``dao`` module.

Command line functions are grouped together by the service being administered.

.. code-block:: bash

   application.py <service> <action> --arguments

Each service is represented by a distinct class which handles the parsing
and evaluation of all actions related to that service. These classes are
ultimetly inherited by the ``CLIParser`` class, which acts as the primary
command line interface for interacting with the parent application as a whole.

.. note:: Parser classes in this module are based on the ``ArgumentParser``
  class from the `standard Python library <https://docs.python.org/3/library/argparse.html>`_.

Usage Example
-------------

Use the ``CLIParser`` object to parsing and evaluate command line arguments:

.. code-block:: python

   >>> from bank.cli import CLIParser
   >>>
   >>> parser = CLIParser()
   >>>
   >>> # Parse command line arguments but do not evaluate the result
   >>> args = parser.parse_args()
   >>>
   >>> # Parse command line arguments AND evaluate the corresponding function
   >>> parser.execute()

If you want to access the command line interface for just a single service
(E.g., for testing purposes) you can use the dedicated class for that service:

.. code-block:: python

   >>> from bank.cli import AdminParser
   >>>
   >>> admin_parser = AdminParser()
   >>> admin_parser.parse_args()

API Reference
-------------
"""

from __future__ import annotations

from argparse import ArgumentParser
from typing import List

from . import settings, dao, system


class BaseParser(ArgumentParser):
    """Used to extend functionality of the builtin ``ArgumentParser`` class"""

    def __init__(self, **kwargs):
        """Handles the parsing of command line arguments"""

        # If parent init has already been called, there is no need to call it again
        if hasattr(self, 'prog'):
            return

        super(BaseParser, self).__init__(**kwargs)

    def execute(self, args: List[str] = None) -> None:
        """Method used to evaluate the command line parser

        Parse command line arguments and evaluate the corresponding function.
        If arguments are not explicitly passed to this function, they are
        retrieved from the command line.

        Args:
            args: A list of command line arguments
        """

        cli_kwargs = dict(self.parse_args(args)._get_kwargs())
        cli_kwargs.pop('function', self.print_help)(**cli_kwargs)

    def add_subparsers(self, **kwargs):
        """Return a subparser for the parent parser class

        Parser instances are only allowed to have a single subparser. If a
        subparser for the parent parser already exists, return the existing
        parser.
        """

        if self._subparsers:
            return self._subparsers._group_actions[0]

        else:
            return super().add_subparsers(parser_class=BaseParser)


class AdminParser(dao.AdminServices, BaseParser):
    """Command line parser for the ``admin`` service"""

    def __init__(self, **kwargs) -> None:
        BaseParser.__init__(self, **kwargs)

        subparsers = self.add_subparsers()
        admin_parser = subparsers.add_parser('admin', help='Tools for general system status')
        admin_subparsers = admin_parser.add_subparsers(title="admin actions")

        # Reusable definitions for argument help text
        account_help = 'Name of a slurm user account'

        info = admin_subparsers.add_parser('info', help='Print usage and allocation information')
        info.set_defaults(function=super(AdminParser, AdminParser).print_info)
        info.add_argument('--account', dest='self', type=dao.AdminServices, help=account_help)

        notify = admin_subparsers.add_parser('notify', help='Send any pending email notifications')
        notify.set_defaults(function=super(AdminParser, AdminParser).send_pending_alerts)
        notify.add_argument('--account', dest='self', type=dao.AdminServices, help=account_help)

        unlocked = admin_subparsers.add_parser('unlocked', help='List all unlocked user accounts')
        unlocked.set_defaults(function=super(AdminParser, AdminParser).find_unlocked)

        renew = admin_subparsers.add_parser('renew', help='Rollover any expired investments')
        renew.set_defaults(function=super(AdminParser, AdminParser).renew)
        renew.add_argument('--account', dest='self', type=dao.InvestmentServices, help=account_help)


class SlurmParser(system.SlurmAccount, BaseParser):
    """Command line parser for the ``slurm`` service"""

    def __init__(self, **kwargs) -> None:
        BaseParser.__init__(self, **kwargs)

        subparsers = self.add_subparsers(parser_class=BaseParser)
        slurm_parser = subparsers.add_parser('slurm', help='Administrative tools for slurm accounts')
        slurm_subparsers = slurm_parser.add_subparsers(title="slurm actions")

        # Reusable definitions for argument help text
        account_help = 'The slurm account to administrate'
        user_help = 'Optionally create a user under the parent slurm account'

        slurm_create = slurm_subparsers.add_parser('add_acc', help='Create a new slurm account')
        slurm_create.set_defaults(function=super(SlurmParser, SlurmParser).create_account)
        slurm_create.add_argument('--account', dest='account_name', type=dao.SlurmAccount, help=account_help)
        slurm_create.add_argument('--desc', dest='description', type=dao.SlurmAccount, help='The description of the account')
        slurm_create.add_argument('--org', dest='organization', type=dao.SlurmAccount, help='The parent organization of the account')

        slurm_delete = slurm_subparsers.add_parser('delete_acc', help='Delete an existing slurm account')
        slurm_delete.set_defaults(function=super(SlurmParser, SlurmParser).delete_account)
        slurm_delete.add_argument('--account', dest='self', type=dao.SlurmAccount, help=account_help)

        slurm_add_user = slurm_subparsers.add_parser('add_user', help='Add a user to an existing slurm account')
        slurm_add_user.set_defaults(function=super(SlurmParser, SlurmParser).add_user)
        slurm_add_user.add_argument('--account', dest='self', type=dao.SlurmAccount, help=account_help)
        slurm_add_user.add_argument('--user', dest='user_name', help=user_help)

        slurm_delete_user = slurm_subparsers.add_parser('delete_user', help='Remove a user to an existing slurm account')
        slurm_delete_user.set_defaults(function=super(SlurmParser, SlurmParser).delete_user)
        slurm_delete_user.add_argument('--account', dest='self', type=dao.SlurmAccount, help=account_help)
        slurm_delete_user.add_argument('--user', dest='user_name', help=user_help)

        slurm_lock = slurm_subparsers.add_parser('lock', help='Lock a slurm account from submitting any jobs')
        slurm_lock.set_defaults(function=super(SlurmParser, SlurmParser).set_locked_state, lock_state=True)
        slurm_lock.add_argument('--account', dest='self', type=dao.SlurmAccount, help=account_help)

        slurm_unlock = slurm_subparsers.add_parser('unlock', help='Allow a slurm account to submit jobs')
        slurm_unlock.set_defaults(function=super(SlurmParser, SlurmParser).set_locked_state, lock_state=False)
        slurm_unlock.add_argument('--account', dest='self', type=dao.SlurmAccount, help=account_help)


class ProposalParser(dao.ProposalServices, BaseParser):
    """Command line parser for the ``proposal`` service"""

    def __init__(self, **kwargs) -> None:
        BaseParser.__init__(self, **kwargs)

        subparsers = self.add_subparsers()
        proposal_parser = subparsers.add_parser('proposal', help='Administrative tools for user proposals')
        proposal_subparsers = proposal_parser.add_subparsers(title="proposal actions")

        # Reusable definitions for argument help text
        account_help = 'The parent slurm account'

        proposal_create = proposal_subparsers.add_parser('create', help='Create a new proposal for an existing slurm account')
        proposal_create.set_defaults(function=super(ProposalParser, ProposalParser).create_proposal)
        proposal_create.add_argument('--account', dest='self', type=dao.ProposalServices, help=account_help)
        self._add_cluster_args(proposal_create)

        proposal_delete = proposal_subparsers.add_parser('delete', help='Delete an existing account proposal')
        proposal_delete.set_defaults(function=super(ProposalParser, ProposalParser).delete_proposal)
        proposal_delete.add_argument('--account', dest='self', type=dao.ProposalServices, help=account_help)

        proposal_add = proposal_subparsers.add_parser('add', help='Add service units to an existing proposal')
        proposal_add.set_defaults(function=super(ProposalParser, ProposalParser).add)
        proposal_add.add_argument('--account', dest='self', type=dao.ProposalServices, help=account_help)
        self._add_cluster_args(proposal_add)

        proposal_subtract = proposal_subparsers.add_parser('subtract', help='Subtract service units from an existing proposal')
        proposal_subtract.set_defaults(function=super(ProposalParser, ProposalParser).subtract)
        proposal_subtract.add_argument('--account', dest='self', type=dao.ProposalServices, help=account_help)
        self._add_cluster_args(proposal_subtract)

        proposal_overwrite = proposal_subparsers.add_parser('overwrite', help='Overwrite properties of an existing proposal')
        proposal_overwrite.set_defaults(function=super(ProposalParser, ProposalParser).overwrite)
        proposal_overwrite.add_argument('--account', dest='self', type=dao.ProposalServices, help=account_help)
        self._add_cluster_args(proposal_overwrite)

    @staticmethod
    def _add_cluster_args(parser: ArgumentParser) -> None:
        """Add argument definitions to the given command line subparser

        Args:
            parser: The parser to add arguments to
        """

        for cluster in settings.clusters:
            parser.add_argument(f'--{cluster}', type=int, help=f'The {cluster} limit in CPU Hours', default=0)


class InvestmentParser(dao.InvestmentServices, BaseParser):
    """Command line parser for the ``investment`` service"""

    def __init__(self, **kwargs) -> None:
        BaseParser.__init__(self, **kwargs)

        subparsers = self.add_subparsers()
        investment_parser = subparsers.add_parser('investment', help='Administrative tools for user investments')
        investment_subparsers = investment_parser.add_subparsers(title="investment actions")

        # Reusable definitions for argument help text
        account_help = 'The parent slurm account'
        proposal_id_help = 'The investment proposal id'

        investment_create = investment_subparsers.add_parser('create', help='Create a new investment')
        investment_create.set_defaults(function=super(InvestmentParser, InvestmentParser).create_investment)
        investment_create.add_argument('--account', dest='self', type=dao.InvestmentServices, help=account_help)
        investment_create.add_argument('--sus', type=int, help='The number of SUs you want to insert')
        investment_create.add_argument('--num_inv', type=int, default=5, help='Optionally divide service units across n sequential investments')
        investment_create.add_argument('--duration', type=int, default=365, help='The length of each investment')

        investment_delete = investment_subparsers.add_parser('delete', help='Delete an existing investment')
        investment_delete.set_defaults(function=super(InvestmentParser, InvestmentParser).delete_investment)
        investment_delete.add_argument('--account', dest='self', type=dao.InvestmentServices, help=account_help)
        investment_delete.add_argument('--id', type=int, help=proposal_id_help)

        investment_add = investment_subparsers.add_parser('add', help='Add service units to an existing investment')
        investment_add.set_defaults(function=super(InvestmentParser, InvestmentParser).add)
        investment_add.add_argument('--account', dest='self', type=dao.InvestmentServices, help=account_help)
        investment_add.add_argument('--id', type=int, help=proposal_id_help)
        investment_add.add_argument('--sus', type=int, help='The number of SUs you want to insert')

        investment_subtract = investment_subparsers.add_parser('subtract', help='Subtract service units from an existing investment')
        investment_subtract.set_defaults(function=super(InvestmentParser, InvestmentParser).subtract)
        investment_subtract.add_argument('--account', dest='self', type=dao.InvestmentServices, help=account_help)
        investment_subtract.add_argument('--id', type=int, help=proposal_id_help)
        investment_subtract.add_argument('--sus', type=int, help='The number of SUs you want to subtract')

        investment_overwrite = investment_subparsers.add_parser('overwrite', help='Overwrite properties of an existing investment')
        investment_overwrite.set_defaults(function=super(InvestmentParser, InvestmentParser).overwrite)
        investment_overwrite.add_argument('--account', dest='self', type=dao.InvestmentServices, help=account_help)
        investment_overwrite.add_argument('--id', type=int, help=proposal_id_help)
        investment_overwrite.add_argument('--sus', type=int, help='The number of SUs you want the investment to have')

        investment_advance = investment_subparsers.add_parser('advance', help='Move service units from future investments to the current allocation')
        investment_advance.set_defaults(function=super(InvestmentParser, InvestmentParser).advance)
        investment_advance.add_argument('--account', dest='self', type=dao.InvestmentServices, help=account_help)
        investment_advance.add_argument('--sus', type=int, help='The number of SUs you want to advance')


class CLIParser(AdminParser, SlurmParser, ProposalParser, InvestmentParser):
    """Command line parser used as the primary entry point for the parent application"""

    def __init__(self, **kwargs):
        AdminParser.__init__(self, **kwargs)
        SlurmParser.__init__(self, **kwargs)
        ProposalParser.__init__(self, **kwargs)
        InvestmentParser.__init__(self, **kwargs)
