from unittest import TestCase

from sqlalchemy import Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

from bank.orm.mixins import AutoReprMixin

Base = declarative_base()




def create_table_with_mixin(mixin):
    class DummyTable(Base, mixin):
        __tablename__ = 'test_table'

        id = Column(Integer, primary_key=True)
        int_col = Column(Integer)
        str_col = Column(Text)

    return DummyTable