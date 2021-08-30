from sqlalchemy import Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base


def create_table_with_mixin(mixin):

    # Make sure to use a new base class each time, otherwise SQLAlchemy may
    # try to extend the behavior of an existing table
    Base = declarative_base()

    class DummyTable(Base, mixin):
        __tablename__ = 'test_table'

        id = Column(Integer, primary_key=True)
        int_col = Column(Integer)
        str_col = Column(Text)

    return DummyTable
