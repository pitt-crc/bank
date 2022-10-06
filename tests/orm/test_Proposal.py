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
            self.assertEqual(perc, proposal.percent_notified)


class ProposalStatus(TestCase):
    """Test boolean result for the ``is_expired`` property"""

    def test_current_date_before_range(self) -> None:
        """Test the proposal is unexpired before the proposal date range"""

        proposal = Proposal(start_date=TOMORROW, end_date=DAY_AFTER_TOMORROW)
        self.assertFalse(proposal.is_expired, 'Proposal is not expired despite missing allocation')
        self.assertFalse(proposal.is_active, 'Proposal is active despite missing allocation')

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertFalse(proposal.is_expired)
        self.assertFalse(proposal.is_active)

        proposal.allocations[0].final_usage = 1_000
        self.assertFalse(proposal.is_expired)
        self.assertFalse(proposal.is_active)

        proposal.allocations[1].final_usage = 1_000
        self.assertFalse(proposal.is_expired)
        self.assertFalse(proposal.is_active)

    def test_current_date_in_range(self) -> None:
        """Test the proposal is not expired during the proposal date range"""

        proposal = Proposal(start_date=YESTERDAY, end_date=TOMORROW)
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertFalse(proposal.is_expired)
        self.assertTrue(proposal.is_active)

        proposal.allocations[0].final_usage = 1_000
        self.assertFalse(proposal.is_expired)
        self.assertTrue(proposal.is_active)

        proposal.allocations[1].final_usage = 1_000
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

    def test_current_date_after_range(self) -> None:
        """Test the proposal is expired after the proposal date range"""

        proposal = Proposal(start_date=DAY_BEFORE_YESTERDAY, end_date=YESTERDAY)
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

        proposal.allocations[0].final_usage = 1_000
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

        proposal.allocations[1].final_usage = 1_000
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

    def test_current_date_at_start(self) -> None:
        """Test the proposal is unexpired on the start date"""

        proposal = Proposal(start_date=TODAY, end_date=TOMORROW)
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertFalse(proposal.is_expired)
        self.assertTrue(proposal.is_active)

        proposal.allocations[0].final_usage = 1_000
        self.assertFalse(proposal.is_expired)
        self.assertTrue(proposal.is_active)

        proposal.allocations[1].final_usage = 1_000
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

    def test_current_date_at_end(self) -> None:
        """Test the proposal is expired on the end date"""

        proposal = Proposal(start_date=YESTERDAY, end_date=TODAY)
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster, service_units_total=10_000))
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

        proposal.allocations[0].final_usage = 1_000
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)

        proposal.allocations[1].final_usage = 1_000
        self.assertTrue(proposal.is_expired)
        self.assertFalse(proposal.is_active)
