"""The ``settings`` module defines application settings."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Optional, Literal, Tuple, Any

from pydantic import Field
from pydantic_settings import BaseSettings

from bank.system import EmailTemplate

DEFAULT_TEMPLATE_DIR = Path(__file__).resolve().parent / 'templates'
CUSTOM_SETTINGS_DIR = Path('/etc/crc_bank')


class SettingsSchema(BaseSettings):
    """Defines the schema and default values for application settings"""

    # Application Logging
    log_path: Optional[Path] = Field(
        title='Log Path',
        default_factory=lambda: Path(NamedTemporaryFile().name),
        description='Optionally log application events to a file.')

    log_level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR'] = Field(
        title='Logging Level',
        default='INFO',
        description='Application logging level.')

    log_format: str = Field(
        title='Logging Format',
        default='[%(levelname)s] %(asctime)s - %(name)s - %(message)s',
        description='Format used when creating new log entries. Follows the standard Python formatting template.')

    # Database Settings
    db_url: str = Field(
        title='Database Path',
        description='URI for the application database.')

    # SMTP settings
    email_from: str = Field(
        title='Email From Address',
        description='From address for automatically generated emails.')

    email_subject: str = Field(
        title='Email Subject Line',
        default='CRC Disk Usage Alert',
        description='Subject line for automatically generated emails.')

    email_domain: str = Field(
        title='User Email Address Domain',
        description=(
            'String to append to usernames when generating user email addresses. '
            'The leading `@` is optional.'))

    # General Settings
    clusters: Tuple[str, ...] = Field(
        name='Clusters',
        default=tuple(),
        decription=' A list of Slurm cluster names to track usage on.')

    inv_rollover_fraction: float = Field(
        name='Service Unit Rollover',
        default=0,
        description='Fraction of service units (between 0 and 1) to carry over when rolling over investments.')

    date_format: str = Field(
        title='Date Format',
        default='%m/%d/%Y',
        description='Format for expressing dates as strings. Used in CLI parsing, email formatting, and other places.')

    # An email to send when a user has exceeded a proposal usage threshold
    usage_notify_levels: Tuple[int, ...] = Field(
        name='Usage Notification Thresholds',
        default=(90,),
        description='Notify users when they exceeded a percentage of their service units')

    # An email to send when a user is  nearing the end of their proposal
    expiration_notify_days: Tuple[int, ...] = Field(
        name='Expiration Notification Thresholds',
        default=(60,),
        description='Notify users when their proposal is given number of days from expiration.')

    def _load_tempalte_file(self, template_file):
        try:
            return EmailTemplate((CUSTOM_SETTINGS_DIR / template_file).read_text())

        except:
            return EmailTemplate(DEFAULT_TEMPLATE_DIR / template_file)

    @property
    def usage_warning_template(self) -> EmailTemplate:
        return self._load_tempalte_file('usage_warning_email.html')

    @property
    def expiration_warning_template(self) -> EmailTemplate:
        return self._load_tempalte_file('expiration_warning_email.html')

    @property
    def expired_proposal_template(self) -> EmailTemplate:
        return self._load_tempalte_file('expired_proposal_email.html')


class ApplicationSettings:
    """Global application settings object"""

    _parsed_settings: Optional[SettingsSchema] = None

    @classmethod
    def clear_settings(cls) -> None:
        """Clear any previously configured settings"""

        cls._parsed_settings = None

    @classmethod
    def configure(cls, **kwargs) -> None:
        """Instantiate application settings

        Any existing settings not defined s keyword arguments are overwritten
        by default values.
        """

        cls._parsed_settings = SettingsSchema(**kwargs)

    @classmethod
    def configure_from_file(cls, path: Path) -> None:
        """Instantiate application settings using values from a JSON file

        Args:
            path: Json file path to load settings from
        """

        cls._parsed_settings = SettingsSchema.model_validate_json(path.read_text())

    @classmethod
    def _raise_not_configured(cls) -> None:
        """Raise an error if application settings are not configured

        Raises:
            ValueError: If application settings are not configured
        """

        if cls._parsed_settings is None:
            raise ValueError('Settings must be configured before getting/settings individual values.')

    @classmethod
    def set(cls, **kwargs) -> None:
        """Update values in the application settings

        Raises:
            ValueError: If the item name is not a valid setting
        """

        cls._raise_not_configured()
        for item, value in kwargs.items():
            if not hasattr(cls._parsed_settings, item):
                ValueError(f'Invalid settings option: {item}')

            setattr(cls._parsed_settings, item, value)

    @classmethod
    def get(cls, item: str) -> Any:
        """Return a value from application settings

        Args:
            item: Name of the settings value to retrieve

        Returns
           The value currently configured in application settings
        """

        cls._raise_not_configured()
        return getattr(cls._parsed_settings, item)
