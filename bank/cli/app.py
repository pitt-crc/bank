"""The ``cli.app`` module defines the entrypoint for executing
the application from the commandline.
"""

from typing import Type

from .parsers import AdminParser, AccountParser, ProposalParser, InvestmentParser, BaseParser
from .. import __version__


class CommandLineApplication:
    """Commandline application used as the primary entry point for the parent application"""

    def __init__(self):
        """Initialize the application's commandline interface"""

        self.parser = BaseParser()
        self.parser.add_argument('--version', action='version', version=__version__)
        self.subparsers = self.parser.add_subparsers(parser_class=BaseParser, dest='service', required=True)

        # Add desired parsers to the commandline application
        self.add_subparser_to_app(
            'admin',
            AdminParser,
            title='Admin actions',
            help_text='tools for general system administration')

        self.add_subparser_to_app(
            'account',
            AccountParser,
            title='Account actions',
            help_text='tools for managing individual accounts')

        self.add_subparser_to_app(
            'proposal',
            ProposalParser,
            title='Proposal actions',
            help_text='administrative tools for user proposals')

        self.add_subparser_to_app(
            'investment',
            InvestmentParser,
            title='Investment actions',
            help_text='administrative tools for user investments')

    def add_subparser_to_app(
        self,
        command: str,
        parser_class: Type[BaseParser],
        title: str,
        help_text: str
    ) -> None:
        """Add a parser object to the parent commandline application as a subparser

        Args:
            command: The commandline argument used to invoke the given parser
            parser_class: A ``BaseParser`` subclass
            title: The help text title
            help_text: The help text description
        """

        parser = self.subparsers.add_parser(command, help=help_text)
        subparsers = parser.add_subparsers(title=title, dest='command', required=True)
        parser_class.define_interface(subparsers)

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
