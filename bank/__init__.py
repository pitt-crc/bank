"""A banking and proposal system for Slurm."""

import sqlalchemy_utils

import bank.orm
from . import settings
from .orm import DBConnection

__version__ = '0.0.0'

# Configure settings from file
settings_path = settings.CUSTOM_SETTINGS_DIR / 'settings.json'
settings.ApplicationSettings.configure_from_file(settings_path)


# Create database if it does not exist
DBConnection.configure(settings.ApplicationSettings.get('db_url'))
if not sqlalchemy_utils.database_exists(DBConnection.url):
    sqlalchemy_utils.create_database(DBConnection.url)
    DBConnection.metadata.create_all(DBConnection.engine)
