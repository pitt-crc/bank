from datetime import timedelta
from unittest import TestCase

from sqlalchemy import join, select
from dateutil.relativedelta import relativedelta

from bank import settings
from bank.account_logic import ProposalServices
from bank.exceptions import MissingProposalError, ProposalExistsError, SlurmAccountNotFoundError
from bank.orm import Account, Allocation, DBConnection, Proposal
from tests._utils import DAY_AFTER_TOMORROW, DAY_BEFORE_YESTERDAY, EmptyAccountSetup, \
    ProposalSetup, TODAY, TOMORROW, YESTERDAY

joined_tables = join(join(Allocation, Proposal), Account)
sus_query = select(Allocation.service_units) \
    .select_from(joined_tables) \
    .where(Account.name == settings.test_account) \
    .where(Allocation.cluster_name == settings.test_cluster) \
    .where(Proposal.is_active)

active_proposal_query = select(Proposal) \
    .join(Account) \
    .where(Account.name == settings.test_account) \
    .where(Proposal.is_active)


class InitExceptions(EmptyAccountSetup, TestCase):
    """Tests to ensure proposals report that provided account does not exist"""

    def test_error_on_non_existent_account(self) -> None:
        super().setUp()
        with self.assertRaises(SlurmAccountNotFoundError):
            self.account = ProposalServices(settings.non_existent_account)


class CreateProposal(EmptyAccountSetup, TestCase):
    """Test the creation of proposals via the ``create`` method"""

    def setUp(self) -> None:
        super().setUp()
        self.account = ProposalServices(settings.test_account)

    def test_default_sus_are_zero(self) -> None:
        """Test proposals are created with zero service units by default"""

        self.account.create()
        with DBConnection.session() as session:
            query = select(Proposal).join(Account).where(Account.name == settings.test_account)
            proposal = session.execute(query).scalars().first()

            self.assertTrue(proposal)
            for alloc in proposal.allocations:
                self.assertEqual(0, alloc.service_units)

    def test_non_default_sus_are_set(self) -> None:
        """Test proposals are assigned the number of sus specified by kwargs"""

        self.account.create(**{settings.test_cluster: 1000})
        with DBConnection.session() as session:
            service_units = session.execute(sus_query).scalars().first()
            self.assertEqual(1000, service_units)

    def test_error_if_already_exists(self) -> None:
        """Test a ``ProposalExistsError`` error is raised if the proposal already exists"""

        self.account.create()
        with self.assertRaises(ProposalExistsError):
            self.account.create()

    def test_error_on_negative_sus(self) -> None:
        """Test an error is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.create(**{settings.test_cluster: -1})


class DeleteProposal(ProposalSetup, TestCase):
    """Test the deletion of proposals via the ``delete`` method"""

    def setUp(self) -> None:
        super().setUp()
        self.account = ProposalServices(settings.test_account)

    def test_delete_by_id(self) -> None:
        """Test a specific proposal is deleted when an id is given"""

        delete_pid = 1
        self.account.delete(proposal_id=delete_pid)

        with DBConnection.session() as session:
            query = select(Proposal).where(Proposal.id == delete_pid)
            proposal = session.execute(query).first()
            self.assertIsNone(proposal, f'Proposal {delete_pid} was not deleted')


class ModifyDate(ProposalSetup, TestCase):
    """Test the modification of start/end dates via the ``modify_date`` method"""

    def setUp(self) -> None:
        super().setUp()
        self.account = ProposalServices(settings.test_account)

    def test_dates_are_modified(self) -> None:
        """Test start and end dates are overwritten in the proposal"""

        proposal_query = select(Proposal) \
            .join(Account) \
            .where(Account.name == settings.test_account) \
            .order_by(Proposal.start_date.desc())

        with DBConnection.session() as session:
            old_proposal = session.execute(proposal_query).scalars().first()
            proposal_id = old_proposal.id
            new_start_date = old_proposal.start_date + relativedelta(days=100)
            new_end_date = old_proposal.end_date + relativedelta(days=100)

        self.account.modify_date(proposal_id, start=new_start_date, end=new_end_date)

        with DBConnection.session() as session:
            new_proposal = session.execute(proposal_query).scalars().first()
            self.assertEqual(new_start_date, new_proposal.start_date)
            self.assertEqual(new_end_date, new_proposal.end_date)

    def test_error_on_inverted_dates(self) -> None:
        """Test a ``ValueError`` is raised for start when the start date comes before the end date"""

        with self.assertRaises(ValueError):
            self.account.modify_date(end=DAY_BEFORE_YESTERDAY)


class AddSus(ProposalSetup, TestCase):
    """Test the addition of sus via the ``add`` method"""

    def setUp(self) -> None:
        super().setUp()
        self.account = ProposalServices(settings.test_account)

    def test_sus_are_added(self) -> None:
        """Test SUs are added to the proposal"""

        with DBConnection.session() as session:
            original_sus = session.execute(sus_query).scalars().first()

        sus_to_add = 1000
        self.account.add_sus(**{settings.test_cluster: sus_to_add})

        with DBConnection.session() as session:
            new_sus = session.execute(sus_query).scalars().first()
            self.assertEqual(original_sus + sus_to_add, new_sus)

    def test_error_on_bad_cluster_name(self) -> None:
        """Test a ``ValueError`` is raised if the cluster name is not defined in application settings"""

        fake_cluster_name = 'fake_cluster'
        with self.assertRaises(ValueError):
            self.account.add_sus(**{fake_cluster_name: 1000})

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.add_sus(**{settings.test_cluster: -1})


class SubtractSus(ProposalSetup, TestCase):
    """Test the subtraction of sus via the ``subtract`` method"""

    def setUp(self) -> None:
        super().setUp()
        self.account = ProposalServices(settings.test_account)

    def test_sus_are_subtracted(self) -> None:
        """Test SUs are removed from the proposal"""

        with DBConnection.session() as session:
            original_sus = session.execute(sus_query).scalars().first()

        sus_to_subtract = 1000
        self.account.subtract_sus(**{settings.test_cluster: sus_to_subtract})

        with DBConnection.session() as session:
            new_sus = session.execute(sus_query).scalars().first()
            self.assertEqual(original_sus - sus_to_subtract, new_sus)

    def test_error_on_bad_cluster_name(self) -> None:
        """Test a ``ValueError`` is raised if the cluster name is not defined in application settings"""

        with self.assertRaises(ValueError):
            self.account.subtract_sus(fake_cluster_name=1000)

    def test_error_on_negative_sus(self) -> None:
        """Test a ``ValueError`` is raised when assigning negative service units"""

        with self.assertRaises(ValueError):
            self.account.subtract_sus(**{settings.test_cluster: -1})

    def test_error_on_over_subtraction(self) -> None:
        """Test a value error is raised for subtraction resulting in negative sus"""

        with self.assertRaises(ValueError):
            self.account.subtract_sus(**{settings.test_cluster: self.num_proposal_sus + 100})


class MissingProposalErrors(EmptyAccountSetup, TestCase):
    """Tests for errors when manipulating an account that does not have a proposal"""

    def setUp(self) -> None:
        super().setUp()
        self.account = ProposalServices(settings.test_account)

    def test_error_on_delete(self) -> None:
        """Test for a ``MissingProposalError`` error when deleting without a proposal ID"""

        with self.assertRaises(MissingProposalError):
            self.account.delete()

    def test_error_on_modify(self) -> None:
        """Test a ``MissingProposalError`` error is raised when modifying a missing proposal"""

        with self.assertRaises(MissingProposalError):
            self.account.modify_date(**{'start': TODAY, 'proposal_id': 1000})

    def test_error_on_add(self) -> None:
        """Test a ``MissingProposalError`` error is raised when adding to a missing proposal"""

        with self.assertRaises(MissingProposalError):
            self.account.add_sus(**{settings.test_cluster: 1})

    def test_error_on_subtract(self) -> None:
        """Test a ``MissingProposalError`` error is raised when subtracting from a missing proposal"""

        with self.assertRaises(MissingProposalError):
            self.account.subtract_sus(**{settings.test_cluster: 1})


class PreventOverlappingProposals(EmptyAccountSetup, TestCase):
    """Tests to ensure proposals cannot overlap in time"""

    def setUp(self) -> None:
        super().setUp()
        self.account = ProposalServices(settings.test_account)

    def test_neighboring_proposals_are_allowed(self):
        """Test that proposals with neighboring durations are allowed"""

        self.account.create(start=TODAY, end=TODAY+relativedelta(days=1), **{settings.test_cluster: 100})
        self.account.create(start=TOMORROW, end=TOMORROW+relativedelta(days=1), **{settings.test_cluster: 100})

    def test_error_on_proposal_creation(self):
        """Test new proposals are not allowed to overlap with existing proposals"""

        self.account.create(start=TODAY)
        with self.assertRaises(ProposalExistsError):
            self.account.create(start=TODAY)

    def test_error_on_proposal_modification(self):
        """Test existing proposals can not be modified to overlap with other proposals"""

        self.account.create(start=YESTERDAY, end=YESTERDAY+timedelta(days=2), **{settings.test_cluster: 100})
        self.account.create(start=TOMORROW, end=TOMORROW+timedelta(days=2), **{settings.test_cluster: 100})

        with self.assertRaises(ProposalExistsError):
            self.account.modify_date(end=DAY_AFTER_TOMORROW)
