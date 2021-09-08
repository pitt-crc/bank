"""Generic utilities used by the test suite"""

import os
from unittest import TestCase

from bank.orm import engine


class DatabaseSafeTest(TestCase):
    """Base class for the UnitTest framework that protects database transactions"""

    def setUp(self) -> None:
        """Set up a database transaction to be rolled back after tests"""

        self.__transaction = engine.connect().begin()
        super(DatabaseSafeTest, self).setUp()

    def tearDown(self) -> None:
        """Rollback database changes made during testing"""

        self.__transaction.rollback()
        super(DatabaseSafeTest, self).tearDown()


class CleanEnviron:
    """Context manager that restores original environmental variables on exit"""

    def __enter__(self) -> None:
        self._environ = os.environ.copy()
        os.environ.clear()

    def __exit__(self, *args, **kwargs) -> None:
        os.environ.clear()
        os.environ.update(self._environ)
