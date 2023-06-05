"""The ``cli.app`` module defines the entrypoint for executing
the application from the commandline.
"""

from bank import __version__
from .parsers import AdminParser, AccountParser, ProposalParser, InvestmentParser, BaseParser


class CommandLineApplication:
    """Commandline application used as the primary entry point for the parent application"""

    def __init__(self):
        """Initialize the application's commandline interface"""

        self.parser = BaseParser()
        self.parser.add_argument('--version', action='version', version=__version__)
        self.subparsers = self.parser.add_subparsers(parser_class=BaseParser, required=True)

        # Add each application subparser with appropriate help text
        self.subparsers.add_parser(
            name='admin',
            parents=[AdminParser(add_help=False)],
            help='tools for general system administration')

        self.subparsers.add_parser(
            name='account',
            parents=[AccountParser(add_help=False)],
            help='tools for managing individual accounts')

        self.subparsers.add_parser(
            name='proposal',
            parents=[ProposalParser(add_help=False)],
            help='administrative tools for user proposals')

        self.subparsers.add_parser(
            name='investment',
            parents=[InvestmentParser(add_help=False)],
            help='administrative tools for user investments')

    @classmethod
    def execute(cls) -> None:
        """Parse commandline arguments and execute a new instance of the application."""

        cli_kwargs = vars(cls().parser.parse_args())
        executable = cli_kwargs.pop('function')
        executable(**cli_kwargs)
