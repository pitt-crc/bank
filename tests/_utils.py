from datetime import date, timedelta

from sqlalchemy import select

from bank import settings
from bank.orm import Account, Allocation, DBConnection, Investment, Proposal

TODAY = date.today()
TOMORROW = TODAY + timedelta(days=1)
YESTERDAY = TODAY - timedelta(days=1)
DAY_AFTER_TOMORROW = TODAY + timedelta(days=2)
DAY_BEFORE_YESTERDAY = TODAY - timedelta(days=2)

account_subquery = select(Account.id).where(Account.name == settings.test_accounts[0])
account_proposals_query = select(Proposal) \
                          .where(Proposal.account_id.in_(account_subquery))

account_investments_query = select(Investment) \
                            .where(Investment.account_id.in_(account_subquery))

account_proposal_ids_query = select(Proposal.id) \
                     .where(Proposal.account_id.in_(account_subquery))

account_investment_ids_query = select(Investment.id) \
                       .where(Investment.account_id.in_(account_subquery))

active_proposal_query = select(Proposal) \
                        .where(Proposal.account_id.in_(account_subquery)) \
                        .where(Proposal.is_active) \
                        .order_by(Proposal.start_date.desc())

active_investment_query = select(Investment) \
                        .where(Investment.account_id.in_(account_subquery)) \
                        .where(Investment.is_active) \
                        .order_by(Investment.start_date.desc())


def add_proposal_to_test_account(proposal: Proposal) -> None:
    """Add a Proposal to the test account and commit the addition to the database """

    with DBConnection.session() as session:
        account = session.execute(select(Account).where(Account.name == settings.test_accounts[0])).scalars().first()
        account.proposals.extend([proposal])
        session.commit()


def add_investment_to_test_account(investment: Investment) -> None:
    """Add an Investment to the test account and commit the addition to the database """

    with DBConnection.session() as session:
        account = session.execute(select(Account).where(Account.name == settings.test_accounts[0])).scalars().first()
        account.investments.extend([investment])
        session.commit()


class EmptyAccountSetup:
    """Base class used to delete database entries before running tests"""

    def setUp(self) -> None:
        """Delete any proposals and investments that may already exist for the test accounts"""

        with DBConnection.session() as session:

            # Query for existing accounts, removing any that are found
            accounts = session.query(Account).all()
            for account in accounts:
                session.delete(account)

            session.commit()

            # Create new (empty) accounts
            for account in settings.test_accounts:
                session.add(Account(name=account))

            session.commit()


class ProposalSetup(EmptyAccountSetup):
    """Reusable setup mixin for configuring tests against user proposals"""

    num_proposal_sus = 10_000

    def setUp(self) -> None:
        """Ensure there exists a user proposal for the test account with zero service units"""

        super().setUp()

        proposals = []

        # Add proposal with the following date ranges:
        # 2 years ago today - 1 year ago today
        # 1 year ago today - today
        # today - 1 year from today
        # 1 year from today - 2 years from today

        for i in range(-1, 2):
            start = TODAY + ((i - 1) * timedelta(days=365))
            end = TODAY + (i * timedelta(days=365))

            allocations = [Allocation(cluster_name=settings.test_cluster,
                                      service_units_used=0,
                                      service_units_total=self.num_proposal_sus),
                           Allocation(cluster_name='all_clusters',
                                      service_units_used=0,
                                      service_units_total=25_000)]

            proposal = Proposal(
                allocations=allocations,
                start_date=start,
                end_date=end
            )

            proposals.append(proposal)

        add_proposal_to_test_account(proposal)


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
                current_sus=self.num_inv_sus,
                withdrawn_sus=0,
                rollover_sus=0
            )

            add_investment_to_test_account(inv)
