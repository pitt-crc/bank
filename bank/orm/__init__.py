"""The ``orm`` module  provides a `sqlalchemy <https://www.sqlalchemy.org/>`_
based object relational mapper (ORM) for handling database interactions.

SubModules
----------

.. autosummary::
   :nosignatures:

   bank.orm.enum
   bank.orm.tables
"""

import sqlalchemy

from .enum import *
from .tables import *

engine = sqlalchemy.create_engine(settings.db_path)
Session = sqlalchemy.orm.sessionmaker(bind=engine)
