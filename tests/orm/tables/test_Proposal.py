from unittest import TestCase

from bank.orm import Proposal
from bank.settings import app_settings


class TestHasDynamicColumns(TestCase):
    """Test for dynamically added columns based on administered cluster names"""

    def runTest(self) -> None:
        for cluster in app_settings.clusters:
            try:
                getattr(Proposal, cluster)
                
            except AttributeError:
                self.fail(f'Table {Proposal.__tablename__} has no column {cluster}')
