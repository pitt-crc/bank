"""The ``orm`` module  provides a `sqlalchemy <https://www.sqlalchemy.org/>`_
based object relational mapper for handling database interactions. It is
also responsible for defining the schema used by the underlying application
database.
"""
import sqlalchemy

from .enum import *
from .session import ExtendedSession
from .tables import *

engine = sqlalchemy.create_engine(settings.db_path)
Session = sqlalchemy.orm.sessionmaker(bind=engine, class_=ExtendedSession)
