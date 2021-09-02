import json
from datetime import datetime
from unittest import TestCase

from bank.orm.mixins import ExportMixin
from bank.settings import app_settings
from .utils import DummyEnum, create_table_with_mixin

DummyTable = create_table_with_mixin(ExportMixin)


class ExportingToJson(TestCase):
    """Test the exporting of row data to json format"""

    @classmethod
    def setUpClass(cls) -> None:
        cls.test_row = DummyTable(str_col='a', int_col=1, date_col=datetime.now(), enum_col=DummyEnum(1))
        cls.row_as_json = cls.test_row.row_to_json()

    def test_date_format_matches_settings(self) -> None:
        """Test dates are converted to strings using the date format from application settings"""

        # Parse the returned date string and see if it matches the original datetime object
        recovered_date = datetime.strptime(self.row_as_json['date_col'], app_settings.date_format)
        self.assertEqual(recovered_date.date(), self.test_row.date_col.date())

    def test_enum_cast_to_str(self) -> None:
        """Test enum types are cast to strings"""

        self.assertEqual(self.test_row.enum_col.name, self.row_as_json['enum_col'])

    def test_return_is_json_parsable(self) -> None:
        """Test the returned dictionary is parsable by the json package"""

        json.dumps(self.row_as_json)

    def test_includes_all_columns(self) -> None:
        """Test all columns are present in the returned dictionary"""

        for col in self.test_row.__table__.columns:
            self.assertIn(col.name, self.row_as_json)
