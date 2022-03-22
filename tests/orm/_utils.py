"""Generic utilities and mixin classes used when testing the ``orm`` module"""

from typing import Type

from bank import settings
from bank.orm.tables import Base


class ServiceUnitsValidation:
    """Tests for the validation of the service units"""

    db_table_class: Type[Base] = None
    columns_to_test = settings.clusters

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
