import os
from pathlib import Path
from typing import Any, Optional
from unittest import TestCase

from bank.settings import APP_PREFIX, Defaults, Settings, app_settings
from ..utils import CleanEnviron


class DefaultValues(TestCase):
    """Test attribute values match default settings in a clean environment"""

    # noinspection PyMissingOrEmptyDocstring
    def runTest(self) -> None:
        with CleanEnviron():
            for key, value in Defaults.__dict__.items():

                # Ignore attributes that don't map to application settings
                if key.startswith('_'):
                    continue

                self.assertEqual(value, getattr(app_settings, key))


class ReadsEnvironmentalVariables(TestCase):
    """Test environmental variables overwrite default settings"""

    def assert_setting_matches_environment(
            self,
            attr_name: str,
            attr_val: Any,
            env_name: str,
            env_val: Optional[str] = None
    ) -> None:
        """

        Args:
            attr_name:
            attr_val:
            env_name:
            env_val:
        """

        with CleanEnviron():
            os.environ[env_name] = env_val or str(attr_val)
            recovered_value = getattr(Settings(), attr_name)
            self.assertEqual(attr_val, recovered_value)

    def test_pathobj_log_path(self) -> None:
        self.assert_setting_matches_environment(
            'log_path', Path('/this/is/a/path'), APP_PREFIX + 'LOG_PATH')

    def test_boolean_is_testing(self) -> None:
        self.assert_setting_matches_environment(
            'is_testing', False, APP_PREFIX + 'IS_TESTING')

    def test_list_clusters(self) -> None:
        self.assert_setting_matches_environment(
            'clusters', ['c1', 'c2'], APP_PREFIX + 'CLUSTERS', 'c1,c2')

    def test_str_email_suffix(self) -> None:
        self.assert_setting_matches_environment(
            'email_suffix', '@temp.com', APP_PREFIX + 'EMAIL_SUFFIX')
