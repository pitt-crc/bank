from sqlalchemy import Column, Integer, Text, Date

from bank.orm.tables import Base


class DummyTable(Base):
    """A dummy database table for testing purposes"""

    __tablename__ = 'test_table'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    int_col = Column(Integer)
    str_col = Column(Text)
    date_col = Column(Date)
