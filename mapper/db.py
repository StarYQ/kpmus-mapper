import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+psycopg://mapper:mapper@localhost:5432/mapper")


class Base(DeclarativeBase):
    pass


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Session = sessionmaker(engine, expire_on_commit=False)


def init_db(reset=False):
    from mapper import models  # noqa: F401  (registers the tables)
    if reset:
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
