import enum
from typing import Any, Dict, List, Tuple, Union

from sqlalchemy import Column, Date, Enum, Integer, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists

from .settings import app_settings
from .utils import PercentNotified, ProposalType

Base = declarative_base()
metadata = Base.metadata


class CustomBase:
    """Mixin for defining default behavior of ORM classes"""

    def __getitem__(self, item: str) -> Any:
        """Support dictionary like fetching of attribute values"""

        if item not in self.__table__.columns:
            raise KeyError(f'Table `{self.__tablename__}` has no column `{item}`')

        return getattr(self, item)

    def __setitem__(self, key: str, value: Any) -> None:
        """Support dictionary like setting of attribute values"""

        if key not in self.__table__.columns:
            raise KeyError(f'Table `{self.__tablename__}` has no column `{key}`')

        setattr(self, key, value)

    def update(self, **items: Any) -> None:
        """Update column """

        for key in set(items).intersection(self.__table__.columns):
            setattr(self, key, items[key])

    def to_json(self) -> Dict[str, Union[int, str]]:
        """Return the row object as a json compatible dictionary"""

        # Convert data to human readable format
        return_dict = dict()
        for col, value in self:
            if hasattr(value, 'strftime'):
                value = value.strftime(app_settings.date_format)

            elif isinstance(value, enum.Enum):
                value = value.name

            return_dict[col] = value

        return return_dict

    def __iter__(self) -> Tuple[str, Any]:
        """Iterate over pairs of column names and values for the current row"""

        for column in self.__table__.columns:
            yield column.name, getattr(self, column.name)

    def __repr__(self) -> str:
        """Automatically generate a string representation using class attributes"""

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
