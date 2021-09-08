"""The ``orm`` module acts as an object oriented interface for the underlying
application database.

.. sadisplay::
    :module: bank.orm
    :alt: My Schema

"""

import sqlalchemy
import sqlalchemy_utils
from sqlalchemy.orm import sessionmaker

from .tables import Investor, InvestorArchive, Proposal, ProposalArchive, metadata
from ..settings import app_settings

engine = sqlalchemy.create_engine(app_settings.db_path)
Session = sessionmaker(bind=engine, future=True)

if not sqlalchemy_utils.database_exists(engine.url):
    sqlalchemy_utils.create_database(engine.url)
    metadata.create_all(engine)
