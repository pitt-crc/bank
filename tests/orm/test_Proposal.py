"""Tests for the `Proposal`` class."""

from datetime import date, timedelta
import time_machine
from unittest import TestCase

from sqlalchemy import select

from bank import settings
from bank.orm import Account, Allocation, DBConnection, Proposal
from tests._utils import account_proposals_query, add_proposal_to_test_account, DAY_AFTER_TOMORROW, EmptyAccountSetup, TODAY

# Start and End date values to use with time_machine
start = TODAY
end = DAY_AFTER_TOMORROW


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
    """Test boolean ``is_expired`` hybrid property and it's SQL expression form"""

    def test_is_expired_no_allocations(self) -> None:
        """ Test ``is_expired`` for various date ranges on a proposal without any allocations

        On start date --> expired
        Before start date --> not expired
        After start date --> expired
        On end date --> expired
        After end date --> expired

        """

        # Create Proposal and add it to DB
        proposal = Proposal(start_date=start, end_date=end)
        add_proposal_to_test_account(proposal)

        # Test is_exhausted on various dates
        with DBConnection.session() as session:

            proposal = session.execute(account_proposals_query).scalars().first()

            # On start date -> expired
            self.assertTrue(proposal.is_expired)
            self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                       .join(Account)
                                                       .where(Account.name == settings.test_accounts[0])
                                                       .where(Proposal.is_expired)).scalars().all())

            # Before start date -> not expired
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(proposal.is_expired)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())

            # After start date -> expired
            with time_machine.travel(start + timedelta(1)):
                self.assertTrue(proposal.is_expired)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())

            # On End date -> expired
            with time_machine.travel(end):
                self.assertTrue(proposal.is_expired)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())

            # After End date -> expired
            with time_machine.travel(end + timedelta(1)):
                self.assertTrue(proposal.is_expired)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())

    def test_is_expired_active_allocation(self) -> None:
        """ Test ``is_expired`` various date ranges for a proposal with an active allocation

        On start date --> not expired
        Before start date --> not expired
        After start date --> not expired
        On end date --> expired
        After end date --> expired

        """

        # Create Proposal and add it to DB
        proposal = Proposal(start_date=start, end_date=end)
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=0,
                                               service_units_total=10_000))
        add_proposal_to_test_account(proposal)

        # Test is_exhausted on various dates
        with DBConnection.session() as session:

            proposal = session.execute(account_proposals_query).scalars().first()

            # On start date -> not expired
            self.assertFalse(proposal.is_expired)
            self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                          .join(Account)
                                                          .where(Account.name == settings.test_accounts[0])
                                                          .where(Proposal.is_expired)).scalars().all())

            # Before start date -> not expired
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(proposal.is_expired)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_expired)).scalars().all())

            # After start date -> not expired
            with time_machine.travel(start + timedelta(1)):
                self.assertFalse(proposal.is_expired)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_expired)).scalars().all())

            # On End date -> expired
            with time_machine.travel(end):
                self.assertTrue(proposal.is_expired)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())

            # After End date -> expired
            with time_machine.travel(end + timedelta(1)):
                self.assertTrue(proposal.is_expired)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())

    def test_is_expired_mixed_allocations(self) -> None:
        """ Test ``is_expired`` for various date ranges on a proposal with an active allocation and an
        exhausted allocation

        On start date --> not expired
        Before start date --> not expired
        After start date --> not expired
        On end date -->  expired
        After end date --> expired

        """

        # Create Proposal and add it to DB
        proposal = Proposal(start_date=start, end_date=end)
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=0,
                                               service_units_total=10_000))
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=10_000,
                                               service_units_total=10_000))
        add_proposal_to_test_account(proposal)

        # Test is_exhausted on various dates
        with DBConnection.session() as session:

            proposal = session.execute(account_proposals_query).scalars().first()

            # On start date -> not expired
            self.assertFalse(proposal.is_expired)
            self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                          .join(Account)
                                                          .where(Account.name == settings.test_accounts[0])
                                                          .where(Proposal.is_expired)).scalars().all())

            # Before start date -> not expired
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(proposal.is_expired)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_expired)).scalars().all())

            # After start date -> not expired
            with time_machine.travel(start + timedelta(1)):
                self.assertFalse(proposal.is_expired)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_expired)).scalars().all())

            # On End date -> expired
            with time_machine.travel(end):
                self.assertTrue(proposal.is_expired)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())

            # After End date -> expired
            with time_machine.travel(end + timedelta(1)):
                self.assertTrue(proposal.is_expired)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())

    def test_is_expired_exhausted_allocations(self) -> None:
        """ Test ``is_expired`` for various date ranges on a proposal with exhausted allocations

        On start date --> expired
        Before start date --> not expired
        After start date --> expired
        On end date --> expired
        After end date --> expired

        """

        # Create Proposal and add it to DB
        proposal = Proposal(start_date=start, end_date=end)
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=10_000,
                                               service_units_total=10_000))
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=10_000,
                                               service_units_total=10_000))
        add_proposal_to_test_account(proposal)

        # Test is_exhausted on various dates
        with DBConnection.session() as session:

            proposal = session.execute(account_proposals_query).scalars().first()

            # On start date -> expired
            self.assertTrue(proposal.is_expired)
            self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                       .join(Account)
                                                       .where(Account.name == settings.test_accounts[0])
                                                       .where(Proposal.is_expired)).scalars().all())

            # Before start date -> not expired
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(proposal.is_expired)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_expired)).scalars().all())

            # After start date -> expired
            with time_machine.travel(start + timedelta(1)):
                self.assertTrue(proposal.is_expired)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())

            # On End date -> expired
            with time_machine.travel(end):
                self.assertTrue(proposal.is_expired)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())

            # After End date -> expired
            with time_machine.travel(end + timedelta(1)):
                self.assertTrue(proposal.is_expired)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_expired)).scalars().all())


class ActiveProperty(EmptyAccountSetup, TestCase):
    """Test the boolean ``is_active`` hybrid property and it's SQL expression form"""

    def test_is_active_no_allocations(self) -> None:
        """ Test ``is_active`` for various date ranges on a proposal without any allocations

        On start date --> not active
        Before start date --> not active
        After start date --> not active
        On end date --> not active
        After end date --> not active

        """

        # Create Proposal and add it to DB
        proposal = Proposal(start_date=start, end_date=end)
        add_proposal_to_test_account(proposal)

        # Test is_active on various dates
        with DBConnection.session() as session:

            proposal = session.execute(account_proposals_query).scalars().first()

            # On start date
            self.assertFalse(proposal.is_active)
            self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                          .join(Account)
                                                          .where(Account.name == settings.test_accounts[0])
                                                          .where(Proposal.is_active)).scalars().all())

            # Before start date
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

            # After start date
            with time_machine.travel(start + timedelta(1)):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

            # On End date
            with time_machine.travel(end):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

            # After End date
            with time_machine.travel(end + timedelta(1)):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

    def test_is_active_active_allocation(self) -> None:
        """ Test ``is_active`` for various date ranges on a proposal with an active allocation

        On start date --> active
        Before start date --> not active
        After start date --> active
        On end date --> not active
        After end date --> not active

        """

        # Create Proposal and add it to DB
        proposal = Proposal(start_date=start, end_date=end)
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=0,
                                               service_units_total=10_000))
        add_proposal_to_test_account(proposal)

        # Test is_exhausted on various dates
        with DBConnection.session() as session:

            proposal = session.execute(account_proposals_query).scalars().first()

            # On start date
            self.assertTrue(proposal.is_active)
            self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                       .join(Account)
                                                       .where(Account.name == settings.test_accounts[0])
                                                       .where(Proposal.is_active)).scalars().all())

            # Before start date
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

            # After start date
            with time_machine.travel(start + timedelta(1)):
                self.assertTrue(proposal.is_active)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_active)).scalars().all())

            # On End date
            with time_machine.travel(end):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

            # After End date
            with time_machine.travel(end + timedelta(1)):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

    def test_is_active_mixed_allocations(self) -> None:
        """ Test ``is_active`` for various date ranges on a proposal with an active allocation
        and an exhausted allocation

        On start date --> active
        Before start date --> not active
        After start date --> active
        On end date --> not active
        After end date --> not active

        """

        # Create Proposal and add it to DB
        proposal = Proposal(start_date=start, end_date=end)
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=0,
                                               service_units_total=10_000))
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=10_000,
                                               service_units_total=10_000))
        add_proposal_to_test_account(proposal)

        # Test is_exhausted on various dates
        with DBConnection.session() as session:

            proposal = session.execute(account_proposals_query).scalars().first()

            # On start date
            self.assertTrue(proposal.is_active)
            self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                       .join(Account)
                                                       .where(Account.name == settings.test_accounts[0])
                                                       .where(Proposal.is_active)).scalars().all())

            # Before start date
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

            # After start date
            with time_machine.travel(start + timedelta(1)):
                self.assertTrue(proposal.is_active)
                self.assertIn(proposal.id, session.execute(select(Proposal.id)
                                                           .join(Account)
                                                           .where(Account.name == settings.test_accounts[0])
                                                           .where(Proposal.is_active)).scalars().all())

            # On End date
            with time_machine.travel(end):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

            # After End date
            with time_machine.travel(end + timedelta(1)):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

    def test_is_active_exhausted_allocations(self) -> None:
        """ Test ``is_active`` for various date ranges on a proposal with exhausted allocations

        On start date --> not active
        Before start date --> not active
        After start date --> not active
        On end date --> not active
        After end date --> not active

        """

        # Create Proposal and add it to DB
        proposal = Proposal(start_date=start, end_date=end)
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=10_000,
                                               service_units_total=10_000))
        proposal.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                               service_units_used=10_000,
                                               service_units_total=10_000))
        add_proposal_to_test_account(proposal)

        # Test is_exhausted on various dates
        with DBConnection.session() as session:

            proposal = session.execute(account_proposals_query).scalars().first()

            # On start date
            self.assertFalse(proposal.is_active)
            self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                          .join(Account)
                                                          .where(Account.name == settings.test_accounts[0])
                                                          .where(Proposal.is_active)).scalars().all())

            # Before start date
            with time_machine.travel(start - timedelta(1)):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

            # After start date
            with time_machine.travel(start + timedelta(1)):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

            # On End date -> expired
            with time_machine.travel(end):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())

            # After End date -> expired
            with time_machine.travel(end + timedelta(1)):
                self.assertFalse(proposal.is_active)
                self.assertNotIn(proposal.id, session.execute(select(Proposal.id)
                                                              .join(Account)
                                                              .where(Account.name == settings.test_accounts[0])
                                                              .where(Proposal.is_active)).scalars().all())
