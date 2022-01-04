"""Generic utilities and mixin classes used when testing the ``cli`` module"""

import inspect


class CLIAsserts:
    """Mixin class that provides custom assert methods for testing command line parsing"""

    def assert_parser_matches_func_signature(self, cmd: str) -> None:
        """Assert the arguments retrieved from a parsed string match the
        signature of the function they are passed to
        """

        cmd = cmd.split()
        known_args, unknown_args = self.parser.parse_known_args(cmd)
        if unknown_args:
            self.fail(f'Parser received unknown arguments: {unknown_args}')

        parsed_args = dict(known_args._get_kwargs())
        function = parsed_args.pop('function')

        try:
            inspect.getcallargs(function, **parsed_args)

        except Exception as e:
            self.fail(str(e))
