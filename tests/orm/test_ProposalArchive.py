from unittest import TestCase

from bank.orm import ProposalArchive
from bank.settings import app_settings
from tests.orm import base_tests


class ServiceUnitsValidation(TestCase, base_tests.ServiceUnitsValidation):
    """Tests for the validation of the service units"""

    db_table_class = ProposalArchive
    columns_to_test = app_settings.clusters


class HasDynamicColumns(TestCase, base_tests.HasDynamicColumns):
    """Test for dynamically added columns based on administered cluster names"""

    db_table_class = ProposalArchive

    def test_has_usage_columns_for_each_cluster(self) -> None:
        """Test the table has a usage column for each cluster in application settings"""

        for col in app_settings.clusters:
            column_name = col + '_usage'
            try:
                getattr(self.db_table_class, column_name)

            except AttributeError:
                self.fail(f'Table {self.db_table_class.__tablename__} has no column {column_name}')
