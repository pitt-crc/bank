from copy import deepcopy
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select

from bank import settings
from bank.orm import Account, Allocation, DBConnection, Investment, Proposal

TODAY = date.today()
TOMORROW = TODAY + timedelta(days=1)
YESTERDAY = TODAY - timedelta(days=1)
DAY_AFTER_TOMORROW = TODAY + timedelta(days=2)
DAY_BEFORE_YESTERDAY = TODAY - timedelta(days=2)


class EmptyAccountSetup:
    """Base class used to delete database entries before running tests"""

    def setUp(self) -> None:
        """Delete any proposals and investments that may already exist for the test accounts"""

        DBConnection.configure('sqlite:///:memory:')

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

    def setUp(self, start: Optional[date] = None, end: Optional[date] = None) -> None:
        """Ensure there exists a user proposal for the test account with zero service units"""

        super().setUp()

        proposals = []
        if not (start and end):
            # Add proposal with the following date ranges:
            # 2 years ago today - 1 year ago today
            # 1 year ago today - today
            for i in range(-1, 2):
                start = TODAY + ((i - 1) * timedelta(days=365))
                end = TODAY + (i * timedelta(days=365))

                allocations = [Allocation(cluster_name=settings.test_cluster,
                                          service_units_total=self.num_proposal_sus)]
                proposal = Proposal(
                    allocations=allocations,
                    start_date=start,
                    end_date=end
                )
                proposals.append(proposal)
        else:

            # Proposal without allocations
            proposal0 = Proposal(start_date=start, end_date=end)
            proposals.append(proposal0)

            # Proposal with single allocation that is not exhausted
            proposal1 = deepcopy(proposal0)
            proposal1.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                                    service_units_used=0,
                                                    service_units_total=self.num_proposal_sus))
            proposals.append(proposal1)

            # Proposal with an allocation that is exhausted and one that is not
            proposal2 = deepcopy(proposal1)
            proposal2.allocations.append(Allocation(cluster_name=settings.test_cluster,
                                                    service_units_used=0,
                                                    service_units_total=self.num_proposal_sus))
            proposal2.allocations[1].service_units_used = proposal2.allocations[1].service_units_total
            proposals.append(proposal2)

            # Proposal with expired allocations
            proposal3 = deepcopy(proposal2)
            proposal3.allocations[0].service_units_used = proposal3.allocations[0].service_units_total
            proposals.append(proposal3)

        with DBConnection.session() as session:
            account = session.execute(select(Account)
                                      .where(Account.name == settings.test_accounts[0])).scalars().first()
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
                current_sus=self.num_inv_sus,
                withdrawn_sus=0,
                rollover_sus=0
            )
            investments.append(inv)

        with DBConnection.session() as session:
            result = session.execute(select(Account).where(Account.name == settings.test_accounts[0]))
            account = result.scalars().first()
            account.investments.extend(investments)
            session.commit()
