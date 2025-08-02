from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base


def create_session():
    # Create an SQLite database in memory (use 'sqlite:///example.db' for file-based)
    engine = create_engine('sqlite:///example.db')

    # Create all tables
    Base.metadata.create_all(engine)

    # Create a session
    session_factory = sessionmaker(bind=engine)
    session = session_factory()

    return session
