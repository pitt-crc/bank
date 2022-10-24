from unittest import TestCase

from sqlalchemy import select

from bank import settings
from bank.account_logic import AccountServices, AdminServices
from bank.orm import Account, DBConnection, Proposal
from bank.system.slurm import SlurmAccount
from tests._utils import InvestmentSetup, ProposalSetup

active_proposal_query = select(Proposal).join(Account) \
    .where(Account.name == settings.test_account) \
    .where(Proposal.is_active)


class FindUnlockedAccounts(TestCase):
    """Test finding unlocked accounts via the ``find_unlocked`` method"""

    def test_unlocked_account_found(self) -> None:
        """Test that an unlocked account is found"""

        slurm_account = SlurmAccount(settings.test_account)
        slurm_account.set_locked_state(False, settings.test_cluster)

        admin_services = AdminServices()
        self.assertFalse(any(name == slurm_account.account_name for name in admin_services.find_unlocked()))

    def test_locked_account_not_found(self) -> None:
        """Test that a locked account is not found"""

        slurm_account = SlurmAccount(settings.test_account)
        slurm_account.set_locked_state(True, settings.test_cluster)

        admin_services = AdminServices()
        self.assertFalse(any(name == slurm_account.account_name for name in admin_services.find_unlocked()))


class UpdateAccountStatus(ProposalSetup, InvestmentSetup, TestCase):
    """Test update_account_status functionality over multiple accounts"""

    def setUp(self) -> None:
        super().setUp()

        self.account = AccountServices(settings.test_account)
        with DBConnection.session() as session:
            active_proposal = session.execute(active_proposal_query).scalars().first()
            self.proposal_end_date = active_proposal.end_date

    def test_lock_multiple_accounts(self) -> None:
        # TODO: implement
        pass


