from unittest import TestCase

from bank.orm.mixins import ExportMixin
from .utils import create_table_with_mixin

DummyTable = create_table_with_mixin(ExportMixin)


class ExportingToJson(TestCase):
    """Test the exporting of row data to json format"""

    @classmethod
    def setUpClass(cls) -> None:
        pass

    def test_date_format_matches_settings(self) -> None:
        self.fail()

    def test_enum_cast_to_int(self) -> None:
        self.fail()

    def test_return_is_json_parsable(self) -> None:
        self.fail()

    def test_includes_all_columns(self) -> None:
        self.fail()
