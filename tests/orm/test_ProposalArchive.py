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
