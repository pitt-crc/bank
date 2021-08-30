from unittest import TestCase

from sqlalchemy import Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

from bank.orm.mixins import AutoReprMixin

Base = declarative_base()


class DummyTable(Base, AutoReprMixin):
    __tablename__ = 'test_table'
    id = Column(Integer, primary_key=True)
    int_col = Column(Integer)
    str_col = Column(Text)


class StringRepresentation(TestCase):
    """Tests tables with the ``CustomBase`` mixin use custom string casting"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.dummy_obj = DummyTable(int_col=1, str_col='a')
        cls.obj_as_str = str(cls.dummy_obj)

    def test_string_contains_column_values(self) -> None:
        """Test string representations include column values"""

        self.assertIn('int_col=1', self.obj_as_str)
        self.assertIn('str_col=a', self.obj_as_str)

    def test_string_contains_table_name(self) -> None:
        """Test string representations include the table name"""

        self.assertIn(self.dummy_obj.__tablename__, self.obj_as_str)
