from unittest import TestCase

from bank.orm import ProposalArchive
from bank.settings import app_settings


class TestHasDynamicColumns(TestCase):

    def runTest(self) -> None:
        columns = app_settings.clusters + [f'{c}_usage' for c in app_settings.clusters]
        for col in columns:
            try:
                getattr(ProposalArchive, col)

            except AttributeError:
                self.fail(f'Table {ProposalArchive.__tablename__} has no column {col}')
