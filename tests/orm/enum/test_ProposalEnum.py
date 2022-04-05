from unittest import TestCase

from bank.orm.enum import ProposalEnum


class TestCastingFromString(TestCase):
    """Test the creation of new ``ProposalEnum`` instances from string values"""

    def test_cast_unknown(self) -> None:
        """Create an ``Unknown`` instance"""

        self.assertEqual(ProposalEnum.Unknown, ProposalEnum.from_string('Unknown'))

    def test_cast_class(self) -> None:
        """Create an ``Class`` instance"""

        self.assertEqual(ProposalEnum.Class, ProposalEnum.from_string('Class'))

    def test_cast_proposal(self) -> None:
        """Create an ``Proposal`` instance"""

        self.assertEqual(ProposalEnum.Proposal, ProposalEnum.from_string('Proposal'))
