"""Generic utilities and mixin classes used when testing the ``orm`` module"""

from typing import Type

from sqlalchemy import Column, Integer, Text, Date

from bank import settings
from bank.orm.base import CustomBase
from bank.orm.tables import Base


class DummyTable(Base):
    """A dummy database table for testing purposes"""

    __tablename__ = 'test_table'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    int_col = Column(Integer)
    str_col = Column(Text)
    date_col = Column(Date)


class HasDynamicColumns:
    """Test for dynamically added columns based on administered cluster names"""

    db_table_class: Type[CustomBase] = None
    columns_to_test = settings.clusters

    def test_hast_columns_for_each_cluster(self) -> None:
        """Test the table has a column for each cluster in application settings"""

        for col in self.columns_to_test:
            try:
                getattr(self.db_table_class, col)

            except AttributeError:
                self.fail(f'Table {self.db_table_class.__tablename__} has no column {col}')


class ServiceUnitsValidation:
    """Tests for the validation of the service units"""

    db_table_class: Type[CustomBase] = None
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
