from unittest import TestCase

from sqlalchemy import Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

from bank.orm.mixins import CustomBase

Base = declarative_base()


class DummyTable(Base, CustomBase):
    """A dummy table for testing that uses the custom mixin we want to test"""

    __tablename__ = 'test_table'
    id = Column(Integer, primary_key=True)
    int_col = Column(Integer)
    str_col = Column(Text)


class TestClassIsIterable(TestCase):
    """Tests tables with the ``CustomBase`` mixin are iterable"""

    def test_is_iterable(self) -> None:
        """Test instances can be cast to an iterator"""

        iter(DummyTable(int_col=1, str_col='a'))

    def test_cat_to_dict(self) -> None:
        """Test column values are correctly mapped when casting to a dictionary"""

        dummy_obj = DummyTable(int_col=1, str_col='a')
        obj_as_dict = dict(dummy_obj)

        self.assertEqual(dummy_obj.int_col, obj_as_dict['int_col'])
        self.assertEqual(dummy_obj.str_col, obj_as_dict['str_col'])


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
