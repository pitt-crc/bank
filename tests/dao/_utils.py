from bank import settings
from bank.dao import ProposalAccount, InvestorAccount
from bank.orm import Session, Proposal, Investor


class GenericSetup:
    """Base class used to delete database entries before running tests"""

    def setUp(self) -> None:
        """Delete any proposals and investments that may already exist for the test account"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.query(Investor).filter(Investor.account_name == settings.test_account).delete()
            session.commit()


class ProposalSetup(GenericSetup):
    """Reusable setup mixin for configuring tests against user proposals"""

    def setUp(self) -> None:
        """Ensure there exists a user proposal for the test account with zero service units"""

        super().setUp()
        self.account = ProposalAccount(settings.test_account)
        self.account.create_proposal()


class InvestorSetup(ProposalSetup):
    """Reusable setup mixin for configuring tests against user investments"""

    num_inv_sus = 10_000
    inv_id: int = None

    def setUp(self) -> None:
        """Ensure there exists a user proposal and investment for the test user account"""

        super().setUp()
        self.account = InvestorAccount(settings.test_account)
        self.account.create_investment(self.num_inv_sus)
        self.inv_id = self.account._get_investment_info()[0]['id']
