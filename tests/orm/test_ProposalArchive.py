from itertools import chain
from unittest import TestCase

from bank.orm import ProposalArchive
from bank.settings import app_settings


class TestHasDynamicColumns(TestCase):
    """Test for dynamically added columns based on administered cluster names"""

    def runTest(self) -> None:
        for col in chain(app_settings.clusters, (f'{c}_usage' for c in app_settings.clusters)):
            try:
                getattr(ProposalArchive, col)

            except AttributeError:
                self.fail(f'Table {ProposalArchive.__tablename__} has no column {col}')


class ServiceUnitsValidation(TestCase):
    """Tests for the validation of the service units"""

    def test_negative_service_units(self) -> None:
        """Test for a ``ValueError`` when the number of service units are negative"""

        for cluster in app_settings.clusters:
            with self.assertRaises(ValueError):
                ProposalArchive(**{cluster: -1})

    def test_positive_service_units(self) -> None:
        """Test no error is raised when the number of service units are positive"""

        for cluster in app_settings.clusters:
            proposal = ProposalArchive(**{cluster: 10})
            self.assertEqual(10, getattr(proposal, cluster))
