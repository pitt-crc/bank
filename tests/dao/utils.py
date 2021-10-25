from bank.dao import ProposalData
from bank.orm import Session, Proposal
from bank.settings import app_settings


class GenericSetup:
    """Reusable setup mixin for configuring a unittest class"""

    def setUp(self) -> None:
        """Delete any proposals that may already exist for the test account"""

        with Session() as session:
            session.query(Proposal).filter(Proposal.account_name == app_settings.test_account).delete()
            session.commit()

        self.account = ProposalData(app_settings.test_account)
        self.account.create_proposal()
