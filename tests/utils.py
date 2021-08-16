"""Generic utilities used by the test suite"""

import os


class CleanEnviron:
    """Context manager that restores original environmental variables on exit"""

    def __enter__(self) -> None:
        self._environ = os.environ.copy()
        os.environ.clear()

    def __exit__(self, *args, **kwargs) -> None:
        os.environ.clear()
        os.environ.update(self._environ)
