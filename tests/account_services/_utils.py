from typing import List

from bank import settings
from bank.account_services import ProposalServices, InvestmentServices, AdminServices
from bank.orm import Session, Proposal, Investment, ProposalArchive, InvestorArchive


class GenericSetup:
    """Base class used to delete database entries before running tests"""

    def setUp(self) -> None:
        """Delete any proposals and investments that may already exist for the test account"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == settings.test_account).delete()
            session.query(ProposalArchive).filter(ProposalArchive.account_name == settings.test_account).delete()
            session.query(Investment).filter(Investment.account_name == settings.test_account).delete()
            session.query(InvestorArchive).filter(InvestorArchive.account_name == settings.test_account).delete()
            session.commit()


class ProposalSetup(GenericSetup):
    """Reusable setup mixin for configuring tests against user proposals"""

    proposal_id: int
    num_proposal_sus = 10_000

    def setUp(self) -> None:
        """Ensure there exists a user proposal for the test account with zero service units"""

        super().setUp()
        self.account = ProposalServices(settings.test_account)
        self.account.create_proposal(**{settings.test_cluster: self.num_proposal_sus})
        self.session = Session()
        self.proposal_id = self.account.get_proposal(self.session).id

    def tearDown(self) -> None:
        self.session.close()


class InvestorSetup(ProposalSetup):
    """Reusable setup mixin for configuring tests against user investments"""

    inv_id: List[int] = None  # List of ids for investments created during setup
    num_inv_sus = 1_000  # Number of service units PER INVESTMENT
    num_investments = 3

    def setUp(self) -> None:
        """Ensure there exists a user proposal and investment for the test user account"""

        # Create a series of three investments totalling 3,000 service units
        super().setUp()
        self.account = InvestmentServices(settings.test_account)
        self.account.create_investment(self.num_inv_sus * self.num_investments, num_inv=self.num_investments)
        self.inv_id = [inv.id for inv in self.account._get_investment(self.session)]


class AdminSetup(InvestorSetup):
    def setUp(self) -> None:
        """Ensure there exists a user proposal and investment for the test user account"""

        # Create a series of three investments totalling 3,000 service units
        super().setUp()
        self.account = AdminServices(settings.test_account)
