"""The ``cli.app`` module defines the entrypoint for executing
the application from the commandline.
"""

import logging

from bank import __version__
from .parsers import AdminParser, AccountParser, ProposalParser, InvestmentParser, BaseParser
from ..settings import ApplicationSettings, CUSTOM_SETTINGS_DIR


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
    def configure_settings(cls) -> None:
        """Configure application settings from disk"""

        settings_path = CUSTOM_SETTINGS_DIR / 'settings.json'
        ApplicationSettings.configure_from_file(settings_path)

    @classmethod
    def configure_logging(cls) -> None:
        """Configure logging for the parent application and it's dependencies"""

        # Disable log messages from the environment package
        logging.getLogger('environ.environ').setLevel(1000)

        # Configure logging using application settings
        logging.basicConfig(
            filename=ApplicationSettings.get('log_path'),
            format=ApplicationSettings.get('log_format'),
            datefmt=ApplicationSettings.get('date_format'),
            level=ApplicationSettings.get('log_level'),
            filemode='a')

        # Set logging level for third part packages
        for _log_name in ('sqlalchemy.engine', 'environ.environ', 'bank.account_services'):
            logging.getLogger(_log_name).setLevel(ApplicationSettings.get('log_level'))

    @classmethod
    def execute(cls) -> None:
        """Parse commandline arguments and execute a new instance of the application."""

        # Configure the application
        cls.configure_settings()
        cls.configure_logging()

        # Parse and execute command-line arguments
        cli_kwargs = vars(cls().parser.parse_args())
        executable = cli_kwargs.pop('function')
        executable(**cli_kwargs)
