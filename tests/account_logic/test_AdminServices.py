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

    def setUp(self) -> None:
        """Instantiate a SlurmAccount and AdminServices objects for finding account tests"""
        super().setUp()
        self.slurm_account = SlurmAccount(settings.test_account)
        self.admin_services = AdminServices()

    def test_unlocked_account_found(self) -> None:
        """Test that an unlocked account is found"""

        # Unlock the account
        self.slurm_account.set_locked_state(False, settings.test_cluster)

        # The account should be in the list of unlocked accounts
        unlocked_accounts_by_cluster = self.admin_services.find_unlocked_account_names()
        self.assertIn(self.slurm_account.account_name, unlocked_accounts_by_cluster[settings.test_cluster])

    def test_locked_account_not_found(self) -> None:
        """Test that a locked account is not found"""

        # Lock the account
        self.slurm_account.set_locked_state(True, settings.test_cluster)

        # The account should not be in the list of unlocked accounts
        unlocked_accounts_by_cluster = self.admin_services.find_unlocked_account_names()
        self.assertNotIn(self.slurm_account.account_name, unlocked_accounts_by_cluster[settings.test_cluster])


class UpdateAccountStatus(ProposalSetup, InvestmentSetup, TestCase):
    """Test update_account_status functionality over multiple accounts"""

    def setUp(self) -> None:
        """Instantiate AdminServices object for multi-account UpdateAccountStatus"""

        super().setUp()
        self.account = AccountServices(settings.test_account)

    def test_lock_multiple_accounts(self) -> None:
        # TODO: implement
        pass


