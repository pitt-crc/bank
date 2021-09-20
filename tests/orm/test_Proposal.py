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


class TestColumnValueValidation(TestCase):
    """Tests for the validation of values assigned to attributes vis setters"""

    def test_percent_notified_validation(self) -> None:
        """Test for ValueError when percent_notified is not between 0 and 100"""

        with self.assertRaises(ValueError):
            Proposal(percent_notified=-1)

        with self.assertRaises(ValueError):
            Proposal(percent_notified=101)

        Proposal(percent_notified=0)
        Proposal(percent_notified=100)

    def test_percent_notified_setter(self) -> None:
        """Test for ValueError when percent_notified is not between 0 and 100"""

        proposal = Proposal(percent_notified=50)
        self.assertEqual(50, proposal.percent_notified)
