"""Generic utilities used by the test suite"""

from bank import dao
from bank import settings


class ProtectLockState:
    """Restores the test account's lock state after tests are done running"""

    def setUp(self) -> None:
        """Record the initial lock state of the test account"""

        self.initial_state = dao.Account(settings.test_account).get_locked_state()

    def tearDown(self) -> None:
        """Restore the initial lock state of the test account"""

        dao.Account(settings.test_account).set_locked_state(self.initial_state)
