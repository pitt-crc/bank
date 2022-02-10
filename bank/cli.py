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

from argparse import ArgumentParser, Action
from datetime import datetime
from logging import getLogger

from . import settings, dao, system

LOG = getLogger('bank.cli')


class BaseParser(ArgumentParser):
    """Used to extend functionality of the builtin ``ArgumentParser`` class"""

    def __init__(self, **kwargs) -> None:
        """Handles the parsing of command line arguments"""

        # If parent init has already been called, there is no need to call it again
        if hasattr(self, 'prog'):
            return

        super(BaseParser, self).__init__(**kwargs)
        self.set_defaults(function=self.print_help)

    def add_subparsers(self, **kwargs) -> Action:
        """Return a subparser for the parent parser class

        Parser instances are only allowed to have a single subparser. If a
        subparser for the parent parser already exists, return the existing
        parser.
        """

        if self._subparsers:
            return self._subparsers._group_actions[0]

        else:
            return super().add_subparsers(parser_class=BaseParser)


class AdminParser(dao.AdminServices, system.SlurmAccount, BaseParser):
    """Command line parser for the ``admin`` service"""

    def __init__(self, **kwargs) -> None:
        BaseParser.__init__(self, **kwargs)

        subparsers = self.add_subparsers()
        admin_parser = subparsers.add_parser('admin', help='Tools for general account management')
        admin_subparsers = admin_parser.add_subparsers(title="admin actions")

        # Reusable definitions for arguments
        account_definition = dict(dest='self', metavar='acc', help='Name of a slurm user account', required=True)

        info = admin_subparsers.add_parser('info', help='Print account usage and allocation information')
        info.set_defaults(function=super(AdminParser, AdminParser).print_info)
        info.add_argument('--account', type=dao.AdminServices, **account_definition)

        slurm_lock = admin_subparsers.add_parser('lock', help='Lock a slurm account from submitting any jobs')
        slurm_lock.set_defaults(function=super(AdminParser, AdminParser).set_locked_state, lock_state=True)
        slurm_lock.add_argument('--account', type=system.SlurmAccount, **account_definition)

        slurm_unlock = admin_subparsers.add_parser('unlock', help='Allow a slurm account to resume submitting jobs')
        slurm_unlock.set_defaults(function=super(AdminParser, AdminParser).set_locked_state, lock_state=False)
        slurm_unlock.add_argument('--account', type=system.SlurmAccount, **account_definition)

        unlocked = admin_subparsers.add_parser('lock_expired', help='Notify and lock all expired or overdrawn accounts')
        unlocked.set_defaults(function=super(AdminParser, AdminParser).notify_unlocked)

        unlocked = admin_subparsers.add_parser('unlocked', help='List all unlocked user accounts')
        unlocked.set_defaults(function=super(AdminParser, AdminParser).find_unlocked)

        renew = admin_subparsers.add_parser('renew', help='Renew an account\'s proposal and rollover any expired investments')
        renew.set_defaults(function=super(AdminParser, AdminParser).renew)
        renew.add_argument('--account', type=dao.InvestmentServices, **account_definition)


class ProposalParser(dao.ProposalServices, BaseParser):
    """Command line parser for the ``proposal`` service"""

    def __init__(self, **kwargs) -> None:
        BaseParser.__init__(self, **kwargs)

        subparsers = self.add_subparsers()
        proposal_parser = subparsers.add_parser('proposal', help='Administrative tools for user proposals')
        proposal_subparsers = proposal_parser.add_subparsers(title="proposal actions")

        # Reusable definitions for arguments
        account_definition = dict(dest='self', metavar='acc', type=dao.ProposalServices, help='The parent slurm account')

        proposal_create = proposal_subparsers.add_parser('create', help='Create a new proposal for an existing slurm account')
        proposal_create.set_defaults(function=super(ProposalParser, ProposalParser).create_proposal)
        proposal_create.add_argument('--account', **account_definition)
        self._add_cluster_args(proposal_create)

        proposal_delete = proposal_subparsers.add_parser('delete', help='Delete an existing account proposal')
        proposal_delete.set_defaults(function=super(ProposalParser, ProposalParser).delete_proposal)
        proposal_delete.add_argument('--account', **account_definition)

        proposal_add = proposal_subparsers.add_parser('add', help='Add service units to an existing proposal')
        proposal_add.set_defaults(function=super(ProposalParser, ProposalParser).add)
        proposal_add.add_argument('--account', **account_definition)
        self._add_cluster_args(proposal_add)

        proposal_subtract = proposal_subparsers.add_parser('subtract', help='Subtract service units from an existing proposal')
        proposal_subtract.set_defaults(function=super(ProposalParser, ProposalParser).subtract)
        proposal_subtract.add_argument('--account', **account_definition)
        self._add_cluster_args(proposal_subtract)

        proposal_overwrite = proposal_subparsers.add_parser('overwrite', help='Overwrite properties of an existing proposal')
        proposal_overwrite.set_defaults(function=super(ProposalParser, ProposalParser).overwrite)
        proposal_overwrite.add_argument('--account', **account_definition)
        proposal_overwrite.add_argument('--start_date', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new proposal start date')
        proposal_overwrite.add_argument('--end_date', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new proposal end date')
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

        # Reusable definitions for arguments
        account_definition = dict(dest='self', metavar='acc', type=dao.InvestmentServices, help='The parent slurm account')
        proposal_id_definition = dict(type=int, required=True, help='The investment proposal id')
        service_unit_definition = dict(type=int, help='The number of SUs you want to process', required=True)

        investment_create = investment_subparsers.add_parser('create', help='Create a new investment')
        investment_create.set_defaults(function=super(InvestmentParser, InvestmentParser).create_investment)
        investment_create.add_argument('--account', **account_definition)
        investment_create.add_argument('--sus', type=int, help='The number of SUs you want to insert', required=True)
        investment_create.add_argument('--num_inv', type=int, default=5, help='Optionally divide service units across n sequential investments')
        investment_create.add_argument('--duration', type=int, default=365, help='The length of each investment')

        investment_delete = investment_subparsers.add_parser('delete', help='Delete an existing investment')
        investment_delete.set_defaults(function=super(InvestmentParser, InvestmentParser).delete_investment)
        investment_delete.add_argument('--account', **account_definition)
        investment_delete.add_argument('--id', **proposal_id_definition)

        investment_add = investment_subparsers.add_parser('add', help='Add service units to an existing investment')
        investment_add.set_defaults(function=super(InvestmentParser, InvestmentParser).add)
        investment_add.add_argument('--account', **account_definition)
        investment_add.add_argument('--id', **proposal_id_definition)
        investment_add.add_argument('--sus', **service_unit_definition)

        investment_subtract = investment_subparsers.add_parser('subtract', help='Subtract service units from an existing investment')
        investment_subtract.set_defaults(function=super(InvestmentParser, InvestmentParser).subtract)
        investment_subtract.add_argument('--account', **account_definition)
        investment_subtract.add_argument('--id', **proposal_id_definition)
        investment_subtract.add_argument('--sus', **service_unit_definition)

        investment_overwrite = investment_subparsers.add_parser('overwrite', help='Overwrite properties of an existing investment')
        investment_overwrite.set_defaults(function=super(InvestmentParser, InvestmentParser).overwrite)
        investment_overwrite.add_argument('--account', **account_definition)
        investment_overwrite.add_argument('--id', **proposal_id_definition)
        investment_overwrite.add_argument('--sus', **service_unit_definition)
        investment_overwrite.add_argument('--start_date', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new investment start date')
        investment_overwrite.add_argument('--end_date', type=lambda date: datetime.strptime(date, settings.date_format).date(), help='Set a new investment end date')

        investment_advance = investment_subparsers.add_parser('advance', help='Move service units from future investments to the current allocation')
        investment_advance.set_defaults(function=super(InvestmentParser, InvestmentParser).advance)
        investment_advance.add_argument('--account', **account_definition)
        investment_advance.add_argument('--sus', **service_unit_definition)


class CLIParser(AdminParser, ProposalParser, InvestmentParser):
    """Command line parser used as the primary entry point for the parent application"""

    def __init__(self, **kwargs) -> None:
        AdminParser.__init__(self, **kwargs)
        ProposalParser.__init__(self, **kwargs)
        InvestmentParser.__init__(self, **kwargs)

    def execute(self, args=None) -> None:
        """Method used to evaluate the command line parser

        Parse command line arguments and evaluate the corresponding function.
        If arguments are not explicitly passed to this function, they are
        retrieved from the command line.

        Args:
            args: A list of command line arguments
        """

        LOG.debug(f'Evaluate CLI with args: {args}')

        try:
            cli_kwargs = dict(self.parse_args(args)._get_kwargs())
            function = cli_kwargs.pop('function', self.print_help)
            function(**cli_kwargs)

        except Exception as err:
            self.error(err)
