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
from typing import Any, Dict, Tuple, Union

from sqlalchemy.orm import declarative_mixin

from bank.settings import app_settings


@declarative_mixin
class DictAccessPatternMixin:
    """Adds support for getting/setting row values via indexing by column name.

    By default, SQLAlchemy tables only support getting data via attributes.
    This class adds support for dictionary-like data access.
    """

    def __getitem__(self, item: str) -> Any:
        """Support dictionary like fetching of attribute values"""

        if item not in self.__table__.columns:
            raise KeyError(f'Table `{self.__tablename__}` has no column `{item}`')

        return getattr(self, item)

    def __setitem__(self, key: str, value: Any) -> None:
        """Support dictionary like setting of attribute values"""

        if key not in self.__table__.columns:
            raise KeyError(f'Table `{self.__tablename__}` has no column `{key}`')

        setattr(self, key, value)

    def update(self, **items: Any) -> None:
        """Update row values with the given values

        Args:
            **items: The column name and new value as keyword arguments
        """

        for key, val in items.items():
            setattr(self, key, val)

    def __iter__(self) -> Tuple[str, Any]:
        """Iterate over pairs of column names and values for the current row"""

        for column in self.__table__.columns:
            yield column.name, getattr(self, column.name)


@declarative_mixin
class ExportMixin:
    """Adds methods for exporting tables to different file formats and data types."""

    def row_to_json(self) -> Dict[str, Union[int, str]]:
        """Return the row object as a json compatible dictionary."""

        # Convert data to human readable format
        return_dict = dict()
        for col in self.__table__.columns:
            value = getattr(self, col.name)

            if hasattr(value, 'strftime'):
                value = value.strftime(app_settings.date_format)

            elif isinstance(value, enum.Enum):
                value = value.name

            return_dict[col.name] = value

        return return_dict


@declarative_mixin
class AutoReprMixin(ExportMixin):
    """Automatically generate human readable representations when casting tables to strings."""

    def __repr__(self) -> str:
        """Return a human readable representation of the entire table row"""

        json_str = json.dumps(self.row_to_json(), indent=2).strip('{}')
        lines = (str(self.__class__.__name__), '---------------', json_str, '')
        return '\n'.join(lines)


class CustomBase(DictAccessPatternMixin, AutoReprMixin, ExportMixin):
    """Custom SQLAlchemy base class that incorporates all available mixins."""
