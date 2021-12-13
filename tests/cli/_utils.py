"""Generic utilities and mixin classes used when testing the ``orm`` module"""

import inspect


class CLIAsserts:
    """Mixin class that provides custom assert methods for testing command line parsing"""

    def assert_parser_matches_func_signature(self, cmd: str) -> None:
        """Assert the arguments retrieved from a parsed match the
        signature of the function they are passed to
        """

        cmd = cmd.split()
        parsed_args = dict(self.parser.parse_args(cmd)._get_kwargs())
        function = parsed_args.pop('function')

        try:
            inspect.getcallargs(function, *parsed_args.items())

        except Exception as e:
            self.fail(str(e))
