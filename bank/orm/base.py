"""Extends the default functionality of SQLAlchemy tables

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
    """Custom SQLAlchemy base class that adds methods for exporting data to different file formats and data types."""

    def row_to_dict(self, columns: Optional[Collection[str]] = None) -> dict:
        """Return row data as a dictionary

        Returns:
            A dictionary mapping column names to column values
        """

        columns = columns or (c.name for c in self.__table__.columns)
        return {column: getattr(self, column) for column in columns}

    def row_to_json(self, columns: Optional[Collection[str]] = None) -> Dict[str, Union[int, str]]:
        """Return the row object as a json compatible dictionary

        Args:
            columns: Columns to include in the returned dictionary (defaults to all columns)

        Returns:
            A dictionary mapping column names to column values cast as JSON compatible types
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
