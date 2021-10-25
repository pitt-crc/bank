"""The ``orm`` module  provides a `sqlalchemy <https://www.sqlalchemy.org/>`_
based object relational mapper for handling database interactions. It is
also responsible for defining the schema used by the underlying application
database.

Database Schema
---------------

.. sadisplay::
    :module: bank.orm
    :alt: My Schema
"""

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from .tables import Investor, InvestorArchive, Proposal, ProposalArchive, metadata
from ..settings import app_settings

engine = sqlalchemy.create_engine(app_settings.db_path)
Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
