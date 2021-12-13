import json
from datetime import datetime
from unittest import TestCase

from bank import settings
from ._utils import DummyTable


class RowToDict(TestCase):
    """Test the exporting of row data to a dictionary"""

    @classmethod
    def setUpClass(cls) -> None:
        """Create an instance of the ``DummyTable`` class to test against"""

        cls.test_row = DummyTable(str_col='a', int_col=1, date_col=datetime.now())
        cls.row_as_dict = cls.test_row.row_to_dict()

    def test_entries_match_row_data(self) -> None:
        """Test all columns are present in the returned dictionary"""

        for col, value in self.row_as_dict.items():
            self.assertEqual(getattr(self.test_row, col), value)


class RowToJson(TestCase):
    """Test the exporting of row data to json format"""

    @classmethod
    def setUpClass(cls) -> None:
        """Create an instance of the ``DummyTable`` class to test against"""

        cls.test_row = DummyTable(str_col='a', int_col=1, date_col=datetime.now())
        cls.row_as_json = cls.test_row.row_to_json()

    def test_date_format_matches_settings(self) -> None:
        """Test dates are converted to strings using the date format from application settings"""

        # Parse the returned date string and see if it matches the original datetime object
        recovered_date = datetime.strptime(self.row_as_json['date_col'], settings.date_format)
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


class RowToAscii(TestCase):
    """Test the exporting of row data to a string"""

    def test_has_json_content(self) -> None:
        """Test the returned string is not empty"""

        test_row = DummyTable(str_col='a', int_col=1, date_col=datetime.now())
        json_str = json.dumps(test_row.row_to_json()).strip('{}').replace(' ', '').replace('\n', '')
        ascii_str = test_row.row_to_ascii_table().replace(' ', '').replace('\n', '')
        self.assertIn(json_str, ascii_str)
