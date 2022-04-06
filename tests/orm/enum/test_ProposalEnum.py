from unittest import TestCase

from bank.orm.enum import ProposalEnum


class CastingFromString(TestCase):
    """Test the creation of new ``ProposalEnum`` instances from string values"""

    def test_cast_for_unknown_type(self) -> None:
        """Create an ``Unknown`` instance"""

        self.assertEqual(ProposalEnum.Unknown, ProposalEnum.from_string('Unknown'))

    def test_cast_for_class_type(self) -> None:
        """Create an ``Class`` instance"""

        self.assertEqual(ProposalEnum.Class, ProposalEnum.from_string('Class'))

    def test_cast_for_proposal_type(self) -> None:
        """Create an ``Proposal`` instance"""

        self.assertEqual(ProposalEnum.Proposal, ProposalEnum.from_string('Proposal'))

    def test_value_error_on_invalid(self) -> None:
        """Test ``ValueError`` is used for unknown types"""

        with self.assertRaises(ValueError):
            ProposalEnum.from_string('fakestr')


class CastingToString(TestCase):
    """Test casting of ``ProposalEnum`` instances into strings"""

    def runTest(self) -> None:
        self.assertEqual('Class', str(ProposalEnum.Class))
