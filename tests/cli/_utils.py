import inspect


class CLIAsserts:

    def assert_parser_matches_func(self, cmd: str) -> None:
        cmd = cmd.split()
        parsed_args = dict(self.parser.parse_args(cmd)._get_kwargs())
        function = parsed_args.pop('function')

        try:
            inspect.getcallargs(function, *parsed_args.items())

        except Exception as e:
            self.fail(str(e))
