import enum
from typing import Any, Dict, Tuple, Union

from sqlalchemy.orm import declarative_mixin

from bank.settings import app_settings


@declarative_mixin
class DictAccessPatternMixin:
    """Allows values in a table row to be accessed via indexing in addition to as attributes"""

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
        """Update column"""

        for key, val in items.items():
            setattr(self, key, val)

    def __iter__(self) -> Tuple[str, Any]:
        """Iterate over pairs of column names and values for the current row"""

        for column in self.__table__.columns:
            yield column.name, getattr(self, column.name)


@declarative_mixin
class AutoReprMixin:
    """Automatically generate a string representation using class attributes"""

    def __repr__(self) -> str:
        attr_text = (f'{col.name}={getattr(self, col.name)}' for col in self.__table__.columns)
        return f'<{self.__tablename__}(' + ', '.join(attr_text) + ')>'


@declarative_mixin
class ExportMixin:
    def to_json(self) -> Dict[str, Union[int, str]]:
        """Return the row object as a json compatible dictionary"""

        # Convert data to human readable format
        return_dict = dict()
        for col in self.__table.columns:
            value = getattr(self, col)

            if hasattr(value, 'strftime'):
                value = value.strftime(app_settings.date_format)

            elif isinstance(value, enum.Enum):
                value = value.name

            return_dict[col] = value

        return return_dict


class CustomBase(DictAccessPatternMixin, AutoReprMixin, ExportMixin):
    """Custom SQLAlchemy base class for incorporating all available mixins"""
