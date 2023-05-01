"""Tests for the ``Allocation`` class"""

from unittest import TestCase

from bank import settings
from bank.orm import Allocation


class TotalServiceUnitsValidation(TestCase):
    """Tests for the validation of the ``service_units_total`` column"""

    def test_negative_service_units(self) -> None:
        """Test for a ``ValueError`` when the total number of service units is negative"""

        with self.assertRaisesRegex(ValueError, 'non-negative'):
            Allocation(service_units_total=-1)

    def test_value_is_assigned(self) -> None:
        """Test the validated value is assigned to the table instance"""

        for num_sus in (0, 10):
            allocation = Allocation(service_units_total=num_sus)
            self.assertEqual(num_sus, allocation.service_units_total)


class UsedServiceUnitsValidation(TestCase):
    """Tests for the validation of the ``service_units_used`` column"""

    def test_negative_service_units(self) -> None:
        """Test for a ``ValueError`` when the total number of service units is negative"""

        with self.assertRaisesRegex(ValueError, 'non-negative'):
            Allocation(service_units_used=-1)

    def test_value_is_assigned(self) -> None:
        """Test the validated value is assigned to the table instance"""

        for num_sus in (0, 10):
            allocation = Allocation(service_units_used=num_sus)
            self.assertEqual(num_sus, allocation.service_units_used)

    def test_can_exceed_total(self) -> None:
        """Test the used service units are allowed to exceed the total allocated service units"""

        allocation = Allocation(service_units_total=100, service_units_used=105)
        self.assertGreater(allocation.service_units_used, allocation.service_units_total)
        self.assertEqual(100, allocation.service_units_total)
        self.assertEqual(105, allocation.service_units_used)


class ClusterNameValidation(TestCase):
    """Tests for the validation of the ``cluster_name`` column"""

    def test_value_is_assigned(self) -> None:
        """Test the validated value is assigned to the database instance"""

        allocation = Allocation(cluster_name=settings.test_cluster)
        self.assertEqual(settings.test_cluster, allocation.cluster_name)

    def test_missing_cluster(self) -> None:
        """Test for a ``ValueError`` when the cluster name is not defined in settings"""

        with self.assertRaisesRegex(ValueError, 'application settings'):
            Allocation(cluster_name='fake_cluster')

    def test_blank_name(self) -> None:
        """Test for a ``ValueError`` when the cluster name is blank"""

        with self.assertRaisesRegex(ValueError, 'application settings'):
            Allocation(cluster_name='')


# TODO: add isExhausted test
#class ExhaustedProperty(EmptyAccountSetup, TestCase):
