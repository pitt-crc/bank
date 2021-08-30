import sqlalchemy
import sqlalchemy_utils
from sqlalchemy.orm import sessionmaker

from .tables import Investor, InvestorArchive, Proposal, ProposalArchive, metadata
from ..settings import app_settings

# Connect to the correct backend database depending on whether or not the test suite is running
_use_path = app_settings.db_test_path if app_settings.is_testing else app_settings.db_path
engine = sqlalchemy.create_engine(f'sqlite:///{_use_path}')
Session = sessionmaker(engine, future=True)

if not sqlalchemy_utils.database_exists(engine.url):
    sqlalchemy_utils.create_database(engine.url)
    metadata.create_all(engine)
