from unittest import TestCase

from sqlalchemy import Column, Integer, Text
from sqlalchemy.ext.declarative import declarative_base

from bank.orm.mixins import DictAccessPatternMixin

Base = declarative_base()


class DummyTable(Base, DictAccessPatternMixin):
    __tablename__ = 'test_table'
    id = Column(Integer, primary_key=True)
    int_col = Column(Integer)
    str_col = Column(Text)


class TestClassIsIterable(TestCase):
    """Test subclassed tables are iterable"""

    def test_is_iterable(self) -> None:
        """Test instances can be cast to an iterator"""

        iter(DummyTable(int_col=1, str_col='a'))

    def test_cat_to_dict(self) -> None:
        """Test column values are correctly mapped when casting to a dictionary"""

        dummy_obj = DummyTable(int_col=1, str_col='a')
        obj_as_dict = dict(dummy_obj)

        self.assertEqual(dummy_obj.int_col, obj_as_dict['int_col'])
        self.assertEqual(dummy_obj.str_col, obj_as_dict['str_col'])


class TestKeyIndexing(TestCase):
    """Test subclassed tables support key based indexing"""

    def test_get_item(self) -> None:
        table_row = DummyTable(int_col=1, str_col='a')
        self.assertEqual(table_row.int_col, table_row['int_col'])
        self.assertEqual(table_row.str_col, table_row['str_col'])

    def test_set_item(self) -> None:
        table_row = DummyTable(int_col=1, str_col='a')
        table_row['str_col'] = 'b'
        self.assertEqual('b', table_row.str_col)
        self.assertEqual('b', table_row['str_col'])


class TestUpdate(TestCase):
    """Tests for the ``update`` method"""

    def test_row_is_updated(self) -> None:
        table_row = DummyTable(int_col=1, str_col='a')
        new_values = dict(int_col=2, str_col='b')

        table_row.update(**new_values)
        self.assertEqual(new_values['int_col'], table_row.int_col)
        self.assertEqual(new_values['str_col'], table_row.str_col)
