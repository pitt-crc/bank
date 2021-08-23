from datetime import datetime
from typing import Any, Dict, Tuple, Union

from sqlalchemy import Column, Date, Enum, Integer, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists
import enum
from .settings import app_settings
from .utils import PercentNotified, ProposalType

Base = declarative_base()
metadata = Base.metadata


class CustomBase:
    """Mixin for defining default behavior of ORM classes"""

    @classmethod
    def check_matching_entry_exists(cls, **kwargs) -> bool:
        return Session().query(cls).filter_by(**kwargs).first() is not None

    def to_json(self) -> Dict[str, Union[int, str]]:
        out = dict()
        for k, v in self:
            if hasattr(v, 'strftime'):
                v = v.strftime(app_settings.date_format)

            elif isinstance(v, enum.Enum):
                v = v.name

            out[k] = v

        return out

    def __iter__(self) -> Tuple[str, Any]:
        for column in self.__table__.columns:
            yield column.name, getattr(self, column.name)

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
    percent_notified = Column(Enum(PercentNotified))
    proposal_type = Column(Enum(ProposalType))


class ProposalArchive(Base, CustomBase):
    __tablename__ = 'proposal_archive'

    id = Column(Integer, primary_key=True)
    account = Column(Text)
    start_date = Column(Date)
    end_date = Column(Date)


# Dynamically add columns for each of the managed clusters
for cluster in app_settings.clusters:
    setattr(Proposal, cluster, Column(Integer))
    setattr(ProposalArchive, cluster, Column(Integer))
    setattr(ProposalArchive, cluster + '_usage', Column(Integer))

# Connect to the correct backend database depending on whether or not the test suite is running
_use_path = app_settings.db_test_path if app_settings.is_testing else app_settings.db_path
engine = create_engine(f'sqlite:///{_use_path}')

if not database_exists(engine.url):
    create_database(engine.url)
    metadata.create_all(engine)

Session = sessionmaker(engine, future=True)
