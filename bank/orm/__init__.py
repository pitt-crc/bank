"""The ``orm`` module acts as an object oriented interface for the underlying
application database.

.. sadisplay::
    :module: bank.orm
    :alt: My Schema

"""

import sqlalchemy
from sqlalchemy.orm import sessionmaker

#from .enum import ProposalType
from .tables import Investor_Type, InvestorArchive, Proposal_Type, ProposalArchive, metadata
from ..settings import app_settings

engine = sqlalchemy.create_engine(app_settings.db_path)
Session = sessionmaker(bind=engine, future=True)
