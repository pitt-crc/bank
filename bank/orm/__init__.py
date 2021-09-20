"""An object oriented interface for the underlying application database.

.. sadisplay::
    :module: bank.orm
    :alt: My Schema

"""

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from .enum import ProposalType
from .tables import Investor, InvestorArchive, Proposal, ProposalArchive, metadata
from ..settings import app_settings

engine = sqlalchemy.create_engine(app_settings.db_path)
Session = sessionmaker(bind=engine, future=True)
