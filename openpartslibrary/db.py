from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pandas as pd

import uuid

from datetime import datetime

from .models import Base, Part


class PartsLibrary:
    def __init__(self):
        import os
        sqlite_path = os.path.join(os.path.dirname(__file__), 'data', 'parts.db') 
        print(sqlite_path)
        self.engine = create_engine('sqlite:///' + sqlite_path)

        Base.metadata.create_all(self.engine)

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

    def delete_all(self):
        self.session.query(Part).delete()
        self.session.commit()

    def create_parts_from_spreadsheet(self, file_path):
        df = pd.read_excel(file_path)

        parts = []
        for _, row in df.iterrows():
            part = Part(
                uuid=row["uuid"],
                number=row["number"],
                name=row["name"],
                description=row.get("description", "No description"),
                revision=str(row.get("revision", "1")),
                lifecycle_state=row.get("lifecycle_state", "In Work"),
                owner=row.get("owner", "system"),
                date_created=row.get("date_created", datetime.utcnow()),
                date_modified=row.get("date_modified", datetime.utcnow()),
                material=row.get("material"),
                mass=row.get("mass"),
                dimension_x=row.get("dimension_x"),
                dimension_y=row.get("dimension_y"),
                dimension_z=row.get("dimension_z"),
                quantity=row.get("quantity", 0),
                cad_reference=row.get("cad_reference"),
                attached_documents_reference=row.get("attached_documents_reference"),
                lead_time=row.get("lead_time"),
                make_or_buy=row.get("make_or_buy"),
                supplier=row.get("supplier"),
                manufacturer_number=row.get("manufacturer_number"),
                unit_price=row.get("unit_price"),
                currency=row.get("currency")
            )
            parts.append(part)

        self.session.add_all(parts)
        self.session.commit()
        print(f"Imported {len(parts)} parts successfully from {file_path}")
