"""The ``orm`` module  provides a `sqlalchemy <https://www.sqlalchemy.org/>`_
based object relational mapper for handling database interactions. It is
also responsible for defining the schema used by the underlying application
database.
"""

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from .tables import Investor, InvestorArchive, Proposal, ProposalArchive, metadata
from ..system import Settings

engine = sqlalchemy.create_engine(Settings().db_path)
Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
