"""A banking and proposal system for Slurm.

For a command line interface to this package, see the ``crc_bank.py`` file
included with the source code of this application.
"""

import logging

import sqlalchemy_utils

from . import orm
from . import settings

# Temporarily disable log messages from the environment package
logging.getLogger('environ.environ').setLevel('ERROR')

# Configure logging using application settings
logging.basicConfig(
    filename=settings.log_path,
    format=settings.log_format,
    datefmt=settings.date_format,
    level=settings.log_level,
    filemode='a')

# Set logging level for third part packages
for _log_name in ('sqlalchemy.engine', 'environ.environ', 'bank.dao'):
    logging.getLogger(_log_name).setLevel(settings.log_level)

# Create database if it does not exist
if not sqlalchemy_utils.database_exists(orm.engine.url):
    sqlalchemy_utils.create_database(orm.engine.url)
    orm.metadata.create_all(orm.engine)
