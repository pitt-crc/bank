from datetime import timedelta, date

from sqlalchemy import select

from bank import settings
from bank.orm import Session, Proposal, Investment, Account, Allocation, ProposalEnum

TODAY = date.today()
TOMORROW = TODAY + timedelta(days=1)
YESTERDAY = TODAY - timedelta(days=1)
DAY_AFTER_TOMORROW = TODAY + timedelta(days=2)
DAY_BEFORE_YESTERDAY = TODAY - timedelta(days=2)


class EmptyAccountSetup:
    """Base class used to delete database entries before running tests"""

    def setUp(self) -> None:
        """Delete any proposals and investments that may already exist for the test account"""

        with Session() as session:
            account = session.query(Account).filter(Account.name == settings.test_account).first()
            if account is not None:
                session.delete(account)

            session.commit()
            # Create a new (empty) account
            session.add(Account(name=settings.test_account))
            session.commit()


class ProposalSetup(EmptyAccountSetup):
    """Reusable setup mixin for configuring tests against user proposals"""

    num_proposal_sus = 10_000

    def setUp(self) -> None:
        """Ensure there exists a user proposal for the test account with zero service units"""

        super().setUp()

        proposals = []
        for i in range(3):
            start = TODAY + ((i - 1) * timedelta(days=365))
            end = TODAY + (i * timedelta(days=365))
            allocations = [Allocation(cluster_name=settings.test_cluster, service_units=self.num_proposal_sus)]
            proposal = Proposal(proposal_type=ProposalEnum.Proposal, allocations=allocations, start_date=start, end_date=end)
            proposals.append(proposal)

        with Session() as session:
            account = session.execute(select(Account).where(Account.name == settings.test_account)).scalars().first()
            account.proposals.extend(proposals)
            session.commit()


class InvestmentSetup(EmptyAccountSetup):
    """Reusable setup mixin for configuring tests against user investments"""

    num_inv_sus = 1_000  # Number of service units PER INVESTMENT

    def setUp(self) -> None:
        """Ensure there exists a user investment for the test user account"""

        super().setUp()
        investments = []
        for i in range(3):
            start = TODAY + ((i - 1) * timedelta(days=365))
            end = TODAY + (i * timedelta(days=365))
            inv = Investment(
                start_date=start,
                end_date=end,
                service_units=self.num_inv_sus,
                current_sus=5_000,
                withdrawn_sus=100,
                rollover_sus=0
            )
            investments.append(inv)

        with Session() as session:
            result = session.execute(select(Account).where(Account.name == settings.test_account))
            account = result.scalars().first()
            account.investments.extend(investments)
            session.commit()
