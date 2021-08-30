from unittest import TestCase

from bank.orm.mixins import AutoReprMixin
from utils import create_table_with_mixin

DummyTable = create_table_with_mixin(AutoReprMixin)


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
