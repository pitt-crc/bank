from bank.dao import ProposalData, InvestorData
from bank.orm import Session, Proposal, Investor
from bank.settings import app_settings


class GenericSetup:
    def setUp(self) -> None:
        """Delete any proposals and invesments that may already exist for the test account"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == app_settings.test_account).delete()
            session.query(Investor).filter(Investor.account_name == app_settings.test_account).delete()
            session.commit()


class ProposalSetup(GenericSetup):
    """Reusable setup mixin for configuring a unittest class"""

    def setUp(self) -> None:
        """Delete any proposals that may already exist for the test account"""

        super().setUp()
        self.account = ProposalData(app_settings.test_account)
        self.account.create_proposal()


class InvestorSetup(ProposalSetup):
    """Reusable setup mixin for configuring a unittest class"""

    num_inv_sus = 10_000

    def setUp(self) -> None:
        """Delete any proposals that may already exist for the test account"""

        super().setUp()
        self.account = InvestorData(app_settings.test_account)
        self.account.create_investment(self.num_inv_sus)
