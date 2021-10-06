"""Tests for the ``RequireRoot`` class"""

from unittest import TestCase

from bank.system import RequireRoot


class FailsWithoutRoot(TestCase):
    """Tests for the enforcement of root permissions"""

    def test_wrapped_function_errors_without_root(self) -> None:
        """Test that wrapped functions fail when run without root permissions"""

        @RequireRoot
        def test_func() -> None:
            """A dummy test function"""

        with self.assertRaises(PermissionError):
            test_func()
