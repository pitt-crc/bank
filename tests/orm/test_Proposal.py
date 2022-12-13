"""Tests for the `Proposal`` class."""
from datetime import date, timedelta
from unittest import TestCase

from sqlalchemy import select, not_

from bank import settings
from bank.orm import Account, DBConnection, Proposal
from tests._utils import DAY_AFTER_TOMORROW, DAY_BEFORE_YESTERDAY, ProposalSetup, TODAY, TOMORROW, YESTERDAY


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


class ExpiredProperty(ProposalSetup, TestCase):
    """Test boolean ``is_expired`` hybrid property"""

    def test_current_date_before_range(self) -> None:
        """Test that a proposal is never expired before its start

        Before the proposal start date, the proposal should not return as
        being expired under any circumstances.

        This is true whether the values are loaded into a python object or
        directly from the database with the equivalent SQL expression.
        """

        super().setUp(TOMORROW, DAY_AFTER_TOMORROW)

        # Gather proposal objects, and test that the values loaded into them evaluate to not yet being expired
        with DBConnection.session() as session:
            proposals = session.execute(
                select(Proposal).join(Account)
                .where(Account.name == settings.test_accounts[0])
            ).scalars().all()

            for proposal in proposals:
                self.assertFalse(proposal.is_expired)

            # Query for expired proposals using the equivalent SQL expression for is_expired as a filter
            expired_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(Proposal.is_expired)
            ).all()

            self.assertFalse(expired_proposal_ids, "None of the proposals should be expired")

    def test_current_date_in_range(self) -> None:
        """Test that a proposal, when not passed its expiration, is only expired when its allocations are unusable

        When the proposal is within the start/end dates, the proposal should
        only be expired if all of its allocations are either expired (final_usage set when proposal expires)
        or exhausted (all service units consumed).
        """

        # Gather proposal objects, and test that the values loaded into them evaluate to not yet being expired
        super().setUp(start=YESTERDAY, end=TOMORROW)

        with DBConnection.session() as session:
            proposals = session.execute(
                select(Proposal).join(Account)
                .where(Account.name == settings.test_accounts[0])
            ).scalars().all()

            self.assertTrue(proposals[0].is_expired)
            self.assertFalse(proposals[1].is_expired)
            self.assertFalse(proposals[2].is_expired)
            self.assertTrue(proposals[3].is_expired)

            # Query for expired proposals using the equivalent SQL expression for is_expired as a filter
            expired_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(Proposal.is_expired)
            ).scalars().all()

            self.assertIn(1, expired_proposal_ids)
            self.assertNotIn(2, expired_proposal_ids)
            self.assertNotIn(3, expired_proposal_ids)
            self.assertIn(4, expired_proposal_ids)

    def test_current_date_after_range(self) -> None:
        """Test the proposal is always expired after the proposal date range

        The proposal should always return as being expired after the end date
        has passed, no matter the status of associated allocations.
        """

        super().setUp(start=DAY_BEFORE_YESTERDAY, end=YESTERDAY)
        # Gather proposal objects, and test that the values loaded into them evaluate to not yet being expired
        with DBConnection.session() as session:
            proposals = session.execute(
                select(Proposal).join(Account)
                .where(Account.name == settings.test_accounts[0])
            ).scalars().all()

            for proposal in proposals:
                self.assertTrue(proposal.is_expired)

            # Query for active proposals using the equivalent SQL expression for is_expired as a filter
            active_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(not Proposal.is_expired)
            ).all()

            self.assertFalse(active_proposal_ids, "All of the proposals should be expired")

    def test_current_date_at_start(self) -> None:
        """Test the proposal is not expired on the start date"""

        # Gather proposal objects, and test that the values loaded into them evaluate to not yet being expired
        super().setUp(start=TODAY, end=TOMORROW)
        with DBConnection.session() as session:
            proposals = session.execute(
                select(Proposal).join(Account)
                .where(Account.name == settings.test_accounts[0])
            ).scalars().all()

            self.assertTrue(proposals[0].is_expired)
            self.assertFalse(proposals[1].is_expired)
            self.assertFalse(proposals[2].is_expired)
            self.assertTrue(proposals[3].is_expired)

            # Query for expired proposals using the equivalent SQL expression for is_expired as a filter
            expired_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(Proposal.is_expired)
            ).scalars().all()

            self.assertIn(1, expired_proposal_ids)
            self.assertNotIn(2, expired_proposal_ids)
            self.assertNotIn(3, expired_proposal_ids)
            self.assertIn(4, expired_proposal_ids)

    def test_current_date_at_end(self) -> None:
        """Test the proposal is expired on the end date"""

        # Gather proposal objects, and test that the values loaded into them evaluate to not yet being expired
        super().setUp(start=YESTERDAY, end=TODAY)

        with DBConnection.session() as session:
            proposals = session.execute(
                select(Proposal).join(Account)
                .where(Account.name == settings.test_accounts[0])
            ).scalars().all()

            for proposal in proposals:
                self.assertFalse(proposal.is_expired)

            # Query for expired proposals using the equivalent SQL expression for is_expired as a filter
            expired_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(Proposal.is_expired)
            ).all()

            self.assertFalse(expired_proposal_ids, "None of the proposals should be expired")


class ActiveProperty(ProposalSetup, TestCase):
    """Test the boolean ``is_active`` property"""

    def test_current_date_before_range(self) -> None:
        """Test the proposal is not active before the start date

        Before the start date, the proposal should not be active, even if
        there is an associated allocation.
        """

        super().setUp(start=TOMORROW, end=DAY_AFTER_TOMORROW)

        with DBConnection.session() as session:
            proposals = session.execute(
                select(Proposal).join(Account)
                .where(Account.name == settings.test_accounts[0])
            ).scalars().all()

            for proposal in proposals:
                self.assertFalse(proposal.is_active)

            # Query for expired proposals using the equivalent SQL expression for is_expired as a filter
            active_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(Proposal.is_active)
            ).scalars().all()

        self.assertFalse(active_proposal_ids, "None of the proposals should be expired")

    def test_current_date_in_range(self) -> None:
        """Test the proposal is active during the proposal date range

        Proposals within the start/end dates should be active if they have
        allocations that are not yet expired.
        """

        # Create proposal objects, and test that the values loaded into them evaluate to not yet being expired
        super().setUp(start=YESTERDAY, end=TOMORROW)

        with DBConnection.session() as session:
            proposals = session.execute(
                select(Proposal).join(Account)
                .where(Account.name == settings.test_accounts[0])
            ).scalars().all()

            self.assertFalse(proposals[0].is_active)
            self.assertTrue(proposals[1].is_active)
            self.assertTrue(proposals[2].is_active)
            self.assertFalse(proposals[3].is_active)

            # Query for expired proposals using the equivalent SQL expression for is_expired as a filter
            active_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(Proposal.is_active)
            ).scalars().all()

            self.assertNotIn(1, active_proposal_ids)
            self.assertIn(2, active_proposal_ids)
            self.assertIn(3, active_proposal_ids)
            self.assertNotIn(4, active_proposal_ids)

    def test_current_date_after_range(self) -> None:
        """Test the proposal is not active after the end date

        A proposal should never return as active after the end date.
        """

        super().setUp(start=DAY_BEFORE_YESTERDAY, end=YESTERDAY)

        with DBConnection.session() as session:
            proposals = session.execute(
                select(Proposal).join(Account)
                .where(Account.name == settings.test_accounts[0])
            ).scalars().all()

            for proposal in proposals:
                self.assertFalse(proposal.is_active, "All proposals should be expired")

            # Query for expired proposals using the equivalent SQL expression for is_expired as a filter
            active_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(Proposal.is_active)
            ).all()

        self.assertFalse(active_proposal_ids, "All proposals should be expired")

    def test_current_date_at_start(self) -> None:
        """Test the proposal is active on the start date"""

        # Create proposal objects, and test that the values loaded into them evaluate to not yet being expired
        super().setUp(start=TODAY, end=TOMORROW)

        with DBConnection.session() as session:
            proposals = session.execute(
                select(Proposal).join(Account)
                .where(Account.name == settings.test_accounts[0])
            ).scalars().all()

            self.assertFalse(proposals[0].is_active)
            self.assertTrue(proposals[1].is_active)
            self.assertTrue(proposals[2].is_active)
            self.assertFalse(proposals[3].is_active)

            # Query for expired proposals using the equivalent SQL expression for is_expired as a filter
            active_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(Proposal.is_active)
            ).scalars().all()

            self.assertNotIn(1, active_proposal_ids)
            self.assertIn(2, active_proposal_ids)
            self.assertIn(3, active_proposal_ids)
            self.assertNotIn(4, active_proposal_ids)

    def test_current_date_at_end(self) -> None:
        """Test the proposal is not active on the end date

        A proposal should never return as active on its expiration date
        """

        super().setUp(start=YESTERDAY, end=TODAY)

        with DBConnection.session() as session:
            proposals = session.execute(
                select(Proposal).join(Account)
                .where(Account.name == settings.test_accounts[0])
            ).scalars().all()

            for proposal in proposals:
                self.assertFalse(proposal.is_active)

            # Query for expired proposals using the equivalent SQL expression for is_expired as a filter
            active_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(Proposal.is_active)
            ).all()

        self.assertFalse(active_proposal_ids, "None of the proposals should be expired")
