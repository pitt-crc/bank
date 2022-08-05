from unittest import TestCase

from bank import settings
from bank.orm import Allocation


class ServiceUnitsValidation(TestCase):
    """Tests for the validation of the ``service_units`` column"""

    def test_negative_service_units(self) -> None:
        """Test for a ``ValueError`` when the number of service units are negative"""

        with self.assertRaises(ValueError):
            Allocation(service_units=-1)

    def test_value_is_assigned(self) -> None:
        """Test the validated value is assigned to the table instance"""

        for num_sus in (0, 10):
            allocation = Allocation(service_units=num_sus)
            self.assertEqual(num_sus, allocation.service_units)


class ClusterNameValidation(TestCase):
    """Tests for the validation of the ``cluster_name`` column"""

    def test_value_is_assigned(self) -> None:
        """Test the validated value is assigned to the database instance"""

        allocation = Allocation(cluster_name=settings.test_cluster)
        self.assertEqual(settings.test_cluster, allocation.cluster_name)

    def test_invalid_cluster_name(self) -> None:
        """Test for a ``ValueError`` when the cluster name is not defined in settings"""

        fake_name = 'fake_cluster'
        self.assertNotIn(
            fake_name, settings.clusters,
            'Cannot run this test with a real cluster name.')

        with self.assertRaises(ValueError):
            Allocation(cluster_name=fake_name)
