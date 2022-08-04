"""A banking and proposal system for Slurm."""

import logging

import sqlalchemy_utils

import bank.orm
from . import orm
from . import settings

__version__ = 'development'
__author__ = 'Pitt Center for Research Computing'

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
for _log_name in ('sqlalchemy.engine', 'environ.environ', 'bank.account_services'):
    logging.getLogger(_log_name).setLevel(settings.log_level)

# Create database if it does not exist
if not sqlalchemy_utils.database_exists(orm.engine.url):
    sqlalchemy_utils.create_database(orm.engine.url)
    bank.orm.metadata.create_all(orm.engine)
