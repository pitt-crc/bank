"""Generic tests that can be reused for multiple data base tables"""

from typing import Type

from bank.orm.base import CustomBase
from bank.settings import app_settings


class HasDynamicColumns:
    """Test for dynamically added columns based on administered cluster names"""

    db_table_class: Type[CustomBase] = None

    def test_hast_columns_for_each_cluster(self) -> None:
        """Test the table has a column for each cluster in application settings"""

        for col in app_settings.clusters:
            try:
                getattr(self.db_table_class, col)

            except AttributeError:
                self.fail(f'Table {self.db_table_class.__tablename__} has no column {col}')


class ServiceUnitsValidation:
    """Tests for the validation of the service units"""

    db_table_class: Type[CustomBase] = None
    columns_to_test = app_settings.clusters

    def test_negative_service_units(self) -> None:
        """Test for a ``ValueError`` when the number of service units are negative"""

        for cluster in self.columns_to_test:
            with self.assertRaises(ValueError):
                self.db_table_class(**{cluster: -1})

    def test_positive_service_units(self) -> None:
        """Test no error is raised when the number of service units are positive"""

        for cluster in self.columns_to_test:
            table_instance = self.db_table_class(**{cluster: 10})
            self.assertEqual(10, getattr(table_instance, cluster))
