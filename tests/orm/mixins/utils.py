import enum
from typing import Type

from sqlalchemy import Column, Date, Enum, Integer, Text
from sqlalchemy.ext.declarative import declarative_base


class DummyEnum(enum.Enum):
    one = 1
    two = 2
    three = 3


def create_table_with_mixin(*mixins: Type):
    """Create a dummy SQLAlchemy table with the given mixins

    Columns in the returned table and their data types:
        id (Integer)
        int_col (Integer)
        str_col (Text)
        date_col (Date)

    Args:
        *mixins, THe mixins for the returned table

    Returns:
        A child class for the given mixins
    """

    # Make sure to use a new base class each time, otherwise SQLAlchemy may
    # try to extend the behavior of an existing table
    Base = declarative_base()

    class DummyTable(Base, *mixins):
        """A dummy database table for testing purposes"""

        __tablename__ = 'test_table'

        id = Column(Integer, primary_key=True)
        int_col = Column(Integer)
        str_col = Column(Text)
        date_col = Column(Date)
        enum_col = Column(Enum(DummyEnum))

    return DummyTable
