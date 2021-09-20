"""Mixin classes for extending the default behavior of SQLAlchemy tables.

Usage Examples
--------------

Each mixin class provides a different collection of added functionality.
Individual mixins can be added to a table class via inheritance.
For example, to add automatically generated string representation to a
table, create the table in the standard way and include
the ``AutoReprMixin`` class as a parent.

.. doctest:: python

   >>> from bank.orm.mixins import AutoReprMixin
   >>> from sqlalchemy import Column, Integer, Text
   >>> from sqlalchemy.ext.declarative import declarative_base

   >>> Base = declarative_base()
   >>> class ExampleTable(Base, AutoReprMixin):
   ...     __tablename__ = 'example_table'
   ...     id = Column(Integer, primary_key=True)
   ...     my_column = Column(Integer)

   >>> # Here we demonstrate the auto generated string representation
   >>> row = ExampleTable(my_column='some_value')
   >>> print(row)
   <example_table(id=None, my_column=some_value)>

The ``CustomBase`` class provides a convenient way to automatically include
all available mixins:

.. doctest:: python

   >>> from bank.orm.mixins  import CustomBase
   >>> Base = declarative_base(cls=CustomBase)
   >>> class ExampleTable(Base):
   ...     __tablename__ = 'example_table'
   ...     id = Column(Integer, primary_key=True)

API Reference
-------------
"""

import enum
import json
from typing import Collection, Dict, Optional, Union

from sqlalchemy.orm import declarative_mixin

from bank.settings import app_settings


@declarative_mixin
class CustomBase:
    """Custom SQLAlchemy base class that incorporates all available mixins."""

    def row_to_json(self, columns: Optional[Collection[str]] = None) -> Dict[str, Union[int, str]]:
        """Return the row object as a json compatible dictionary.

        Args:
            columns: Columns to include in the returned dictionary (defaults to all columns)
        """

        # Default to using all columns
        columns = columns or (c.name for c in self.__table__.columns)

        # Convert data to human readable format
        return_dict = dict()
        for col in columns:
            value = getattr(self, col)

            if hasattr(value, 'strftime'):
                value = value.strftime(app_settings.date_format)

            elif isinstance(value, enum.Enum):
                value = value.name

            return_dict[col] = value

        return return_dict

    def row_to_ascii_table(self) -> str:
        """Return a human readable representation of the entire table row"""

        json_str = json.dumps(self.row_to_json(), indent=2).strip('{\n}')
        lines = (str(self.__tablename__), '---------------', json_str, '')
        return '\n'.join(lines)
