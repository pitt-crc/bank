"""The ``orm`` module  provides a `sqlalchemy <https://www.sqlalchemy.org/>`_
based object relational mapper for handling database interactions. It is
also responsible for defining the schema used by the underlying application
database.
"""

import sqlalchemy

from .tables import *
from .enum import *
from .. import settings

engine = sqlalchemy.create_engine(settings.db_path)
Session = sqlalchemy.orm.sessionmaker(bind=engine)
