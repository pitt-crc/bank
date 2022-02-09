from unittest import TestCase
from unittest.mock import patch

from bank.system.slurm import RequireRoot


class FailsWithoutRoot(TestCase):
    """Tests for the enforcement of root permissions"""

    @patch.object(RequireRoot, 'check_user_is_root', lambda: False)
    def test_wrapped_function_errors_without_root(self) -> None:
        """Test wrapped functions fail when run without root permissions"""

        @RequireRoot
        def test_func() -> None:
            """A dummy test function"""

        with self.assertRaises(PermissionError):
            test_func()

    @patch.object(RequireRoot, 'check_user_is_root', lambda: True)
    def test_wrapped_function_executed_with_root(self) -> None:
        """Test wrapped functions execute when run with root permissions"""

        @RequireRoot
        def test_func() -> None:
            """A dummy test function"""

        test_func()
