"""The ``orm`` module  provides a `sqlalchemy <https://www.sqlalchemy.org/>`_
based object relational mapper for handling database interactions. It is
also responsible for defining the schema used by the underlying application
database.
"""

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from .tables import Investor, InvestorArchive, Proposal, ProposalArchive, metadata
from .. import settings

engine = sqlalchemy.create_engine(settings.db_path)
Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
