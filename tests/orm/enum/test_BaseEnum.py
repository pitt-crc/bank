from unittest import TestCase

from bank.orm.enum import BaseEnum


class MockEnum(BaseEnum):
    Value0 = 99
    Value1 = 1
    Value2 = 2


class CastingFromString(TestCase):
    """Test the creation of new ``MockEnum`` instances from string values"""

    def test_cast_for_unknown_type(self) -> None:
        """Create an ``Value0`` instance"""

        self.assertEqual(MockEnum.Value0, MockEnum.from_string('Value0'))

    def test_cast_for_class_type(self) -> None:
        """Create an ``Value2`` instance"""

        self.assertEqual(MockEnum.Value2, MockEnum.from_string('Value2'))

    def test_cast_for_proposal_type(self) -> None:
        """Create an ``Value1`` instance"""

        self.assertEqual(MockEnum.Value1, MockEnum.from_string('Value1'))

    def test_value_error_on_invalid(self) -> None:
        """Test ``ValueError`` is used for unknown types"""

        with self.assertRaises(ValueError):
            MockEnum.from_string('fakestr')


class CastingToString(TestCase):
    """Test casting of ``MockEnum`` instances into strings"""

    def runTest(self) -> None:
        self.assertEqual('Value2', str(MockEnum.Value2))
