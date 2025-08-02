from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pandas as pd

import uuid

from .models import Base, Part


class PartsLibrary:
    def __init__(self):
        # Create an SQLite database in memory (use 'sqlite:///example.db' for file-based)
        self.engine = create_engine('sqlite:///example.db')

        # Create all tables
        Base.metadata.create_all(self.engine)

        # Create a session
        self.session_factory = sessionmaker(bind=self.engine)
        self.session = self.session_factory()

    def display(self):
        part_table = pd.read_sql_table(table_name="parts", con=self.engine)

        pd.set_option('display.max_columns', 8)
        pd.set_option('display.width', 200)

        print(part_table)

    def create_part(self, name, number):
        part = Part(uuid=str(uuid.uuid4()), name=name, number=number)
        self.session.add(part)
        self.session.commit()
    
    def read_part(self, uuid):
        part = self.session.query(Part).filter(Part.uuid == uuid).first()
        return part

    def update_part(self):
        pass

    def delete_part(self):
        pass
