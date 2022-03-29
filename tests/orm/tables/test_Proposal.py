from datetime import date, datetime, timedelta
from unittest import TestCase

from bank.orm import Proposal

NOW = datetime.now().date()
TOMORROW = NOW + timedelta(days=1)
YESTERDAY = NOW - timedelta(days=1)
DAY_AFTER_TOMORROW = NOW + timedelta(days=2)
DAY_BEFORE_YESTERDAY = NOW - timedelta(days=2)


class PercentNotifiedValidation(TestCase):
    """Test the validation of the ``percent_notified``` column"""

    def test_percent_notified_out_of_range(self) -> None:
        """Check for a ``ValueError`` when ``percent_notified`` is not between 0 and 100"""

        with self.assertRaises(ValueError):
            Proposal(percent_notified=-1)

        with self.assertRaises(ValueError):
            Proposal(percent_notified=101)

        Proposal(percent_notified=0)
        Proposal(percent_notified=100)


class ExpiredAndActiveProperties(TestCase):
    """Test boolean result for the ``is_expired`` and ``is_active`` properties"""

    @staticmethod
    def make_proposal_with_dates(start: date, end: date) -> Proposal:
        return Proposal(start_date=start, end_date=end)

    def test_current_date_before_range(self) -> None:
        """Test proposal is inactive and unexpired before the proposal date range"""

        proposal = self.make_proposal_with_dates(start=TOMORROW, end=DAY_AFTER_TOMORROW)
        self.assertFalse(proposal.is_active)
        self.assertFalse(proposal.is_expired)

    def current_date_in_range(self) -> None:
        """Test proposal is active and unexpired during the proposal date range"""

        proposal = self.make_proposal_with_dates(start=YESTERDAY, end=TOMORROW)
        self.assertTrue(proposal.is_active)
        self.assertFalse(proposal.is_expired)

    def current_date_after_range(self) -> None:
        """Test proposal is inactive and expired after the proposal date range"""

        proposal = self.make_proposal_with_dates(start=DAY_BEFORE_YESTERDAY, end=YESTERDAY)
        self.assertFalse(proposal.is_active)
        self.assertTrue(proposal.is_expired)

    def current_date_at_start(self) -> None:
        """Test proposal is active and unexpired on the start date"""

        proposal = self.make_proposal_with_dates(start=NOW, end=TOMORROW)
        self.assertTrue(proposal.is_active)
        self.assertFalse(proposal.is_expired)

    def current_date_at_end(self) -> None:
        """Test proposal is inactive and expired on the end date"""

        proposal = self.make_proposal_with_dates(start=YESTERDAY, end=NOW)
        self.assertFalse(proposal.is_active)
        self.assertTrue(proposal.is_expired)
