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
        self.subparsers = self.parser.add_subparsers(parser_class=BaseParser, dest='service', required=True)

        self.subparsers.add_parser('admin', parents=[AdminParser(add_help=False)],  help='tools for general system administration')
        self.subparsers.add_parser('account', parents=[AccountParser(add_help=False)], help='tools for managing individual accounts')
        self.subparsers.add_parser('proposal', parents=[ProposalParser(add_help=False)], help='administrative tools for user proposals')
        self.subparsers.add_parser('investment', parents=[InvestmentParser(add_help=False)], help='administrative tools for user investments')

    @classmethod
    def execute(cls) -> None:
        """Parse commandline arguments and execute the application.

        This method is defined as a class method to provide an executable hook
        for the packaged setup.py file.
        """

        cli_kwargs = vars(cls().parser.parse_args())
        executable = cli_kwargs.pop('function')

        # Remove arguments unused in app logic
        del cli_kwargs['service']
        del cli_kwargs['command']

        # Execute app logic with relevant arguments
        executable(**cli_kwargs)
