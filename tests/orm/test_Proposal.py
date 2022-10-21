"""Tests for the `Proposal`` class."""

from datetime import date, timedelta
from unittest import TestCase

from bank import settings
from bank.orm import Allocation, Proposal
from tests._utils import DAY_AFTER_TOMORROW, DAY_BEFORE_YESTERDAY, TODAY, TOMORROW, YESTERDAY


class PercentNotifiedValidation(TestCase):
    """Test the validation of the ``percent_notified``` column"""

    def test_error_on_out_of_range(self) -> None:
        """Check for a ``ValueError`` when ``percent_notified`` is not between 0 and 100"""

        with self.assertRaises(ValueError):
            Proposal(percent_notified=-1)

        with self.assertRaises(ValueError):
            Proposal(percent_notified=101)

    def test_value_is_assigned(self) -> None:
        """Test the validated value is assigned to the table instance"""

        for perc in (0, 50, 100):
            proposal = Proposal(percent_notified=perc)
            self.assertEqual(perc, proposal.percent_notified, f'Value {perc} was not assigned')


class EndDateValidation(TestCase):
    """Test the validation of the ``end_date``` column"""

    def test_error_before_start_date(self) -> None:
        """Test for a ``ValueError`` when the end date is before the start date"""

        today = date.today()
        yesterday = today - timedelta(days=1)
        with self.assertRaisesRegex(ValueError, 'Value for .* column must come after the proposal start date'):
            Proposal(start_date=today, end_date=yesterday)

    def test_error_on_start_date(self) -> None:
        """Test for a ``ValueError`` when the end date equals the start date"""

        with self.assertRaisesRegex(ValueError, 'Value for .* column must come after the proposal start date'):
            Proposal(start_date=date.today(), end_date=date.today())

    def test_value_is_assigned(self) -> None:
        """Test the validated value is assigned to the table instance"""

        today = date.today()
        tomorrow = today + timedelta(days=1)
        proposal = Proposal(start_date=today, end_date=tomorrow)
        self.assertEqual(tomorrow, proposal.end_date)


class ExpiredProperty(TestCase):
    """Test boolean ``is_expired`` property"""

    def test_current_date_before_range(self) -> None:
        """Test the proposal is always unexpired before the proposal start

        Before the proposal start date, the proposal should not return as
        being expired under any circumstances.
        """

        proposal = Proposal(start_date=TOMORROW, end_date=DAY_AFTER_TOMORROW)
        self.assertFalse(proposal.is_expired)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertFalse(proposal.is_expired)

        proposal.allocations[0].final_usage = 1_000
        self.assertFalse(proposal.is_expired)

    def test_current_date_in_range(self) -> None:
        """Test the proposal is only expired when missing active allocations

        When the proposal is within the start/end dates, the proposal should
        only be expired if there are no available allocations.
        """

        proposal = Proposal(start_date=YESTERDAY, end_date=TOMORROW)
        self.assertTrue(proposal.is_expired)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertFalse(proposal.is_expired)

        proposal.allocations[0].final_usage = 1_000
        self.assertTrue(proposal.is_expired)

    def test_current_date_after_range(self) -> None:
        """Test the proposal is always expired after the proposal date range

        The proposal should always return as being expired after the end date
        has passed, no matter the status of associated allocations.
        """

        proposal = Proposal(start_date=DAY_BEFORE_YESTERDAY, end_date=YESTERDAY)
        self.assertTrue(proposal.is_expired)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertTrue(proposal.is_expired)

        proposal.allocations[0].final_usage = 1_000
        self.assertTrue(proposal.is_expired)

    def test_current_date_at_start(self) -> None:
        """Test the proposal is unexpired on the start date"""

        proposal = Proposal(start_date=TODAY, end_date=TOMORROW)
        self.assertTrue(proposal.is_expired)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertFalse(proposal.is_expired)

        proposal.allocations[0].final_usage = 1_000
        self.assertTrue(proposal.is_expired)

    def test_current_date_at_end(self) -> None:
        """Test the proposal is expired on the end date"""

        proposal = Proposal(start_date=YESTERDAY, end_date=TODAY)
        self.assertTrue(proposal.is_expired)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertTrue(proposal.is_expired)

        proposal.allocations[0].final_usage = 1_000
        self.assertTrue(proposal.is_expired)


class ActiveProperty(TestCase):
    """Test the boolean ``is_active`` property"""

    def test_current_date_before_range(self) -> None:
        """Test the proposal is not active before the start date

        Before the start date, the proposal should not be active, even if
        there is an associated allocation.
        """

        proposal = Proposal(start_date=TOMORROW, end_date=DAY_AFTER_TOMORROW)
        self.assertFalse(proposal.is_active, 'Proposal is active despite missing allocation')

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertFalse(proposal.is_active)

        proposal.allocations[0].final_usage = 1_000
        self.assertFalse(proposal.is_active)

    def test_current_date_in_range(self) -> None:
        """Test the proposal is active during the proposal date range

        Proposals within the start/end dates should be active if they have
        unexpired allocations.
        """

        proposal = Proposal(start_date=YESTERDAY, end_date=TOMORROW)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertTrue(proposal.is_active)

        proposal.allocations[0].final_usage = 1_000
        self.assertFalse(proposal.is_active)

    def test_current_date_after_range(self) -> None:
        """Test the proposal is not active after the end date

        A proposal should never return as active after the end date.
        """

        proposal = Proposal(start_date=DAY_BEFORE_YESTERDAY, end_date=YESTERDAY)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertFalse(proposal.is_active)

        proposal.allocations[0].final_usage = 1_000
        self.assertFalse(proposal.is_active)

    def test_current_date_at_start(self) -> None:
        """Test the proposal is active on the start date"""

        proposal = Proposal(start_date=TODAY, end_date=TOMORROW)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertTrue(proposal.is_active)

        proposal.allocations[0].final_usage = 1_000
        self.assertFalse(proposal.is_active)

    def test_current_date_at_end(self) -> None:
        """Test the proposal is not active on the end date"""

        proposal = Proposal(start_date=YESTERDAY, end_date=TODAY)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertFalse(proposal.is_active)

        proposal.allocations[0].final_usage = 1_000
        self.assertFalse(proposal.is_active)
