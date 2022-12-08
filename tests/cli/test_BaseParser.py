"""Tests for the ``BaseParser`` class."""

from unittest import TestCase

from bank.cli import BaseParser


class DefineInterface(TestCase):
    """Test the ``define_interface`` method"""

    def test_subparser_type(self) -> None:
        """Test the subparser action passed to the method generates ``BaseParser`` instances"""

        class Parser(BaseParser):

            @classmethod
            def define_interface(cls, parent_parser) -> None:
                """Define the commandline interface of the parent parser

                Args:
                    parent_parser: Subparser action to assign parsers and arguments to
                """

                cls.test_parser = parent_parser.add_parser('info')

        self.assertIsInstance(Parser().test_parser, BaseParser)
