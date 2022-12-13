"""Tests for the `Proposal`` class."""
import copy
from datetime import date, timedelta
from unittest import TestCase

from sqlalchemy import select

from bank import settings
from bank.orm import Account, Allocation, DBConnection, Proposal
from tests._utils import DAY_AFTER_TOMORROW, DAY_BEFORE_YESTERDAY, EmptyAccountSetup, TODAY, TOMORROW, YESTERDAY

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


class ExpiredProperty(EmptyAccountSetup, TestCase):
    """Test boolean ``is_expired`` hybrid property"""

    def setUp(self) -> None:
        """Establish connection to temp database"""

        DBConnection.configure('sqlite:///:memory:')
        super().setUp()

    @staticmethod
    def create_test_proposals(self, start, end) -> list[Proposal]:
        """Create set of proposals used across more than one test"""

        # Proposal without allocations
        Proposal1 = Proposal(start_date=start, end_date=end)

        # Proposal with single allocation that is not exhausted
        Proposal2 = copy.deepcopy(Proposal1)
        active_alloc = Allocation(cluster_name=settings.test_cluster, service_units_used=0, service_units_total=10_000)
        Proposal2.allocations.append(active_alloc)

        # Proposal with an allocation that is exhausted and one that is not
        Proposal3 = copy.deepcopy(Proposal2)
        Proposal3.allocations.append(active_alloc)
        Proposal3.allocations[1].service_units_used = Proposal3.allocations[1].service_units_total

        # Proposal with expired allocations
        Proposal4 = copy.deepcopy(Proposal3)
        Proposal4.allocations[0].service_units_used = Proposal3.allocations[0].service_units_total

        return [Proposal1, Proposal2, Proposal3, Proposal4]

    def test_current_date_before_range(self) -> None:
        """Test that a proposal is never expired before its start

        Before the proposal start date, the proposal should not return as
        being expired under any circumstances.

        This is true whether the values are loaded into a python object or
        directly from the database with the equivalent SQL expression.
        """

        # Create proposal objects, and test that the values loaded into them evaluate to not yet being expired
        test_proposals = self.create_test_proposals(start=TOMORROW, end=DAY_AFTER_TOMORROW)

        for proposal in test_proposals:
            self.assertFalse(proposal.is_expired)

        with DBConnection.session() as session:

            # Add proposals to the test account in the database
            account = session.execute(select(Account).where(Account.name == settings.test_accounts[0])).scalars().first()
            account.proposals.extend(test_proposals)
            session.commit()

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

        # Create proposal objects, and test that the values loaded into them evaluate to not yet being expired
        test_proposals = self.create_test_proposals(start=YESTERDAY, end=TOMORROW)
        self.assertTrue(test_proposals[0].is_expired)
        self.assertFalse(test_proposals[1].is_expired)
        self.assertFalse(test_proposals[2].is_expired)
        self.assertTrue(test_proposals[3].is_expired)

        with DBConnection.session() as session:

            # Add proposals to the test account in the database
            account = session.query(Account).filter(Account.name == settings.test_accounts[0]).first()
            account.proposals.extend(test_proposals)
            session.commit()

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

        # Create proposal objects, and test that the values loaded into them evaluate to not yet being expired
        test_proposals = self.create_test_proposals(start=DAY_BEFORE_YESTERDAY, end=YESTERDAY)

        for proposal in test_proposals:
            self.assertTrue(proposal.is_expired)

        with DBConnection.session() as session:
            # Add proposals to the test account in the database
            account = session.execute(
                select(Account).where(Account.name == settings.test_accounts[0])).scalars().first()
            account.proposals.extend(test_proposals)
            session.commit()

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

        # Create proposal objects, and test that the values loaded into them evaluate to not yet being expired
        test_proposals = self.create_test_proposals(start=TODAY, end=TOMORROW)
        self.assertTrue(test_proposals[0].is_expired)
        self.assertFalse(test_proposals[1].is_expired)
        self.assertFalse(test_proposals[2].is_expired)
        self.assertTrue(test_proposals[3].is_expired)

        with DBConnection.session() as session:
            # Add proposals to the test account in the database
            account = session.query(Account).filter(Account.name == settings.test_accounts[0]).first()
            account.proposals.extend(test_proposals)
            session.commit()

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

        # Create proposal objects, and test that the values loaded into them evaluate to not yet being expired
        test_proposals = self.create_test_proposals(start=YESTERDAY, end=TODAY)

        for proposal in test_proposals:
            self.assertFalse(proposal.is_expired)

        with DBConnection.session() as session:
            # Add proposals to the test account in the database
            account = session.execute(
                select(Account).where(Account.name == settings.test_accounts[0])).scalars().first()
            account.proposals.extend(test_proposals)
            session.commit()

            # Query for expired proposals using the equivalent SQL expression for is_expired as a filter
            expired_proposal_ids = session.execute(
                select(Proposal.id)
                .join(Account)
                .where(Account.name == settings.test_accounts[0])
                .where(Proposal.is_expired)
            ).all()

            self.assertFalse(expired_proposal_ids, "None of the proposals should be expired")


class ActiveProperty(EmptyAccountSetup, TestCase):
    """Test the boolean ``is_active`` property"""

    def test_current_date_before_range(self) -> None:
        """Test the proposal is not active before the start date

        Before the start date, the proposal should not be active, even if
        there is an associated allocation.
        """

        proposal = Proposal(start_date=TOMORROW, end_date=DAY_AFTER_TOMORROW)
        self.assertFalse(proposal.is_active, 'Proposal is active despite missing allocation')

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=0,
                                               service_units_total=10_000))
        self.assertFalse(proposal.is_active)

        proposal.allocations[0].service_units_used = proposal.allocations[0].service_units_total
        self.assertFalse(proposal.is_active)

    def test_current_date_in_range(self) -> None:
        """Test the proposal is active during the proposal date range

        Proposals within the start/end dates should be active if they have
        allocations that are not yet expired.
        """

        proposal = Proposal(start_date=YESTERDAY, end_date=TOMORROW)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=0,
                                               service_units_total=10_000))
        self.assertTrue(proposal.is_active)

        proposal.allocations[0].service_units_used = proposal.allocations[0].service_units_total
        self.assertFalse(proposal.is_active)

    def test_current_date_after_range(self) -> None:
        """Test the proposal is not active after the end date

        A proposal should never return as active after the end date.
        """

        proposal = Proposal(start_date=DAY_BEFORE_YESTERDAY, end_date=YESTERDAY)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=0,
                                               service_units_total=10_000))
        self.assertFalse(proposal.is_active)

        proposal.allocations[0].service_units_used = proposal.allocations[0].service_units_total
        self.assertFalse(proposal.is_active)

    def test_current_date_at_start(self) -> None:
        """Test the proposal is active on the start date"""

        proposal = Proposal(start_date=TODAY, end_date=TOMORROW)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=0,
                                               service_units_total=10_000))
        self.assertTrue(proposal.is_active)

        proposal.allocations[0].service_units_used = proposal.allocations[0].service_units_total
        self.assertFalse(proposal.is_active)

    def test_current_date_at_end(self) -> None:
        """Test the proposal is not active on the end date"""

        proposal = Proposal(start_date=YESTERDAY, end_date=TODAY)
        self.assertFalse(proposal.is_active)

        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=0,
                                               service_units_total=10_000))
        self.assertFalse(proposal.is_active)

        proposal.allocations[0].service_units_used = proposal.allocations[0].service_units_total
        self.assertFalse(proposal.is_active)
