from sqlalchemy import Column, Date, Integer, Text
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

Base = declarative_base()
metadata = Base.metadata


class CustomBase:
    """Extends default behavior of the SQLAlchemy ``Base`` class"""

    def __repr__(self) -> str:
        # Automatically generate string representation using class attributes

        attr_text = (f'{key}={val}' for key, val in self.__dict__.items() if not key.startswith('_'))
        return f'<{self.__tablename__}(' + ', '.join(attr_text) + ')>'


class Investor(Base, CustomBase):
    __tablename__ = 'investor'

    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    proposal_type = Column(Integer)
    service_units = Column(Integer)
    current_sus = Column(Integer)
    withdrawn_sus = Column(Integer)
    rollover_sus = Column(Integer)


class InvestorArchive(Base, CustomBase):
    __tablename__ = 'investor_archive'

    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    exhaustion_date = Column(Date)
    service_units = Column(Integer)
    current_sus = Column(Integer)
    proposal_id = Column(Integer)
    investor_id = Column(Integer)


class Proposal(Base, CustomBase):
    __tablename__ = 'proposal'

    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)
    percent_notified = Column(Integer)
    proposal_type = Column(Integer)


class ProposalArchive(Base, CustomBase):
    __tablename__ = 'proposal_archive'

    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)


# Dynamically add columns for each of the managed clusters
for cluster in ['mpi', 'htc', 'gpu', 'smp']:
    setattr(Proposal, cluster, Column(Integer))
    setattr(ProposalArchive, cluster, Column(Integer))
    setattr(ProposalArchive, cluster + '_usage', Column(Integer))

engine = create_engine('sqlite:///crc_bank.db')
if not database_exists(engine.url):
    create_database(engine.url)
    metadata.create_all(engine)

Session = sessionmaker(engine, future=True)
