"""Generic utilities used by the test suite"""
import enum

from sqlalchemy import Column, Integer, Text, Date, Enum

from bank import dao
from bank import settings
from bank.dao import ProposalAccount, InvestorAccount
from bank.orm import Session, Proposal, Investor
from bank.orm.tables import Base


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
        self.inv_id = self.account.get_investment_info()[0]['id']


class ProtectLockState:
    """Restores the test account's lock state after tests are done running"""

    def setUp(self) -> None:
        """Record the initial lock state of the test account"""

        self.initial_state = dao.Account(settings.test_account).get_locked_state()

    def tearDown(self) -> None:
        """Restore the initial lock state of the test account"""

        dao.Account(settings.test_account).set_locked_state(self.initial_state)


class DummyEnum(enum.Enum):
    """A simple enumerated database column"""

    One = 1
    Two = 2
    Three = 3


class DummyTable(Base):
    """A dummy database table for testing purposes"""

    __tablename__ = 'test_table'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    int_col = Column(Integer)
    str_col = Column(Text)
    date_col = Column(Date)
    enum_col = Column(Enum(DummyEnum))
