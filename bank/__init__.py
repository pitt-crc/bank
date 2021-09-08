import logging

from . import settings

# Temporarily disable log messages from the environment package
logging.getLogger('environ.environ').setLevel('ERROR')

# Configure logging using application settings
logging.basicConfig(
    filename=settings.app_settings.log_path,
    format=settings.app_settings.log_format,
    datefmt=settings.app_settings.date_format,
    level=settings.app_settings.log_level,
    filemode='a')

# Set logging level for third part packages
for log_name in ('sqlalchemy.engine', 'environ.environ', 'bank.dao'):
    logging.getLogger(log_name).setLevel(settings.app_settings.log_level)
