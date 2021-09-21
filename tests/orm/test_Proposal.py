"""Tests for the ``Proposal`` class"""

from datetime import date, timedelta
from unittest import TestCase

from bank.orm import Proposal
from bank.settings import app_settings


class HasDynamicColumns(TestCase):
    """Test for dynamically added columns based on administered cluster names"""

    def runTest(self) -> None:
        for cluster in app_settings.clusters:
            try:
                getattr(Proposal, cluster)

            except AttributeError:
                self.fail(f'Table {Proposal.__tablename__} has no column {cluster}')


class PercentNotifiedValidation(TestCase):
    """Tests for the validation of the ``percent_notified``` column"""

    def test_percent_notified_out_of_range(self) -> None:
        """Test for a ``ValueError`` when ``percent_notified`` is not between 0 and 100"""

        with self.assertRaises(ValueError):
            Proposal(percent_notified=-1)

        with self.assertRaises(ValueError):
            Proposal(percent_notified=101)

        Proposal(percent_notified=0)
        Proposal(percent_notified=100)

    def test_percent_notified_in_range(self) -> None:
        """Test no error is raised when ``percent_notified`` is not between 0 and 100"""

        proposal = Proposal(percent_notified=50)
        self.assertEqual(50, proposal.percent_notified)


class ServiceUnitsValidation(TestCase):
    """Tests for the validation of the service units"""

    def test_negative_service_units(self) -> None:
        """Test for a ``ValueError`` when the number of service units are negative"""

        for cluster in app_settings.clusters:
            with self.assertRaises(ValueError):
                Proposal(**{cluster: -1})

    def test_positive_service_units(self) -> None:
        """Test no error is raised when the number of service units are positive"""

        for cluster in app_settings.clusters:
            proposal = Proposal(**{cluster: 10})
            self.assertEqual(10, getattr(proposal, cluster))


class TOArchiveObject(TestCase):
    """Test the conversion of a proposal to an archive object"""

    def setUp(self) -> None:
        """Create a proposal instance for testing"""

        self.proposal = Proposal(
            account_name='username',
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
            percent_notified=10,
            proposal_type=1
        )

        for i, cluster in enumerate(app_settings.clusters):
            setattr(self.proposal, cluster, i)

    def test_correct_column_values(self) -> None:
        """Test the attributes of the returned object match the original proposal"""

        # We could do something clever here with sets and dictionaries
        # Instead lets keep it simple and just check each column one at a time
        archive_obj = self.proposal.to_archive_object()
        self.assertEqual(self.proposal.id, archive_obj.id)
        self.assertEqual(self.proposal.account_name, archive_obj.account_name)
        self.assertEqual(self.proposal.start_date, archive_obj.start_date)
        self.assertEqual(self.proposal.end_date, archive_obj.end_date)
        self.assertEqual(self.proposal.proposal_type, archive_obj.proposal_type)
        for cluster in app_settings.clusters:
            self.assertEqual(getattr(self.proposal, cluster), getattr(archive_obj, cluster))
