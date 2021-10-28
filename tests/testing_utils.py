"""Generic utilities used by the test suite"""

import os

from bank.dao import ProposalData, InvestorData
from bank.orm import Session, Proposal, Investor
from bank.settings import app_settings


class GenericSetup:
    """Base class used to delete database entries before running tests"""

    def setUp(self) -> None:
        """Delete any proposals and investments that may already exist for the test account"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == app_settings.test_account).delete()
            session.query(Investor).filter(Investor.account_name == app_settings.test_account).delete()
            session.commit()


class ProposalSetup(GenericSetup):
    """Reusable setup mixin for configuring tests against user proposals"""

    def setUp(self) -> None:
        """Ensure there exists a user proposal for the test account with zero service units"""

        super().setUp()
        self.account = ProposalData(app_settings.test_account)
        self.account.create_proposal()


class InvestorSetup(ProposalSetup):
    """Reusable setup mixin for configuring tests against user investments"""

    num_inv_sus = 10_000

    def setUp(self) -> None:
        """Ensure there exists a user proposal and investment for the test user account"""

        super().setUp()
        self.account = InvestorData(app_settings.test_account)
        self.account.create_investment(self.num_inv_sus)


class CleanEnviron:
    """Context manager that restores original environmental variables on exit"""

    def __enter__(self) -> None:
        self._environ = os.environ.copy()
        os.environ.clear()

    def __exit__(self, *args, **kwargs) -> None:
        os.environ.clear()
        os.environ.update(self._environ)
