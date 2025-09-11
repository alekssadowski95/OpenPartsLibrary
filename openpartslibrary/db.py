from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pandas as pd

from datetime import datetime

from .models import Base, Part, Supplier, File, Component, ComponentComponent

import uuid

import os


class PartsLibrary:
    def __init__(self, db_path=None):
        if db_path is not None:
            sqlite_path = db_path
        else:
            sqlite_path = os.path.join(os.path.dirname(__file__), 'data', 'parts.db') 
        print(sqlite_path)
        self.engine = create_engine('sqlite:///' + sqlite_path)

        Base.metadata.create_all(self.engine)

        self.session_factory = sessionmaker(bind=self.engine)
        self.session = self.session_factory()

    def display(self):
        # Print the components table to the terminal
        component_component_table = pd.read_sql_table(table_name="component_component", con=self.engine)
        print('ComponentComponent:')
        print('===================')
        print(component_component_table)
        print('')

        # Print the components table to the terminal
        components_table = pd.read_sql_table(table_name="components", con=self.engine)
        print('Components:')
        print('===========')
        print(components_table)
        print('')

        # Print the parts table to the terminal
        part_table = pd.read_sql_table(table_name="parts", con=self.engine)
        print('Parts:')
        print('======')
        print(part_table)
        print('')

        # Print the suppliers table to the terminal
        supplier_table = pd.read_sql_table(table_name="suppliers", con=self.engine)
        print('Suppliers:')
        print('==========')
        print(supplier_table)
        print('')

        # Print the files table to the terminal
        files_table = pd.read_sql_table(table_name="files", con=self.engine)
        print('Files:')
        print('==========')
        print(files_table)
        print('')

    def display_reduced(self):
        # Print the parts table to the terminal in reduced form
        pass

    def display_parts(self):
        # Print the parts table to the terminal
        part_table = pd.read_sql_table(table_name="parts", con=self.engine)
        print('Parts:')
        print('======')
        print(part_table)
        print('')

    def display_suppliers(self):
        # Print the suppliers table to the terminal
        supplier_table = pd.read_sql_table(table_name="suppliers", con=self.engine)
        print('Suppliers:')
        print('==========')
        print(supplier_table)
        print('')

    def display_files(self):
        # Print the files table to the terminal
        files_table = pd.read_sql_table(table_name="files", con=self.engine)
        print('Files:')
        print('==========')
        print(files_table)
        print('')

    def delete_all(self):
        print('[ INFO ] Clearing the parts library.')
        self.session.query(ComponentComponent).delete()
        self.session.query(Component).delete()
        self.session.query(Part).delete()
        self.session.query(Supplier).delete()
        self.session.query(File).delete()
        self.session.commit()

        directory_to_empty = os.path.join(os.path.dirname(__file__), 'data', 'files')
        
        for filename in os.listdir(directory_to_empty):
            filepath = os.path.join(directory_to_empty, filename)
            if os.path.isfile(filepath) and filename != "README.md":
                os.remove(filepath)
                print(f"[ INFO ] Deleted: {filename}")

    def total_value(self):
        from decimal import Decimal
        all_parts = self.session.query(Part).all()

        total_value = Decimal(0.0)
        for part in all_parts:
            total_value = Decimal(total_value) + (Decimal(part.unit_price) * part.quantity)

        return total_value

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
                manufacturer_number=row.get("manufacturer_number"),
                unit_price=row.get("unit_price"),
                currency=row.get("currency")
            )
            parts.append(part)

        self.session.add_all(parts)
        self.session.commit()
        print(f"Imported {len(parts)} parts successfully from {file_path}")
    
    def create_suppliers_from_spreadsheet(self, file_path):
        self.session.query(Supplier).delete()
        self.session.commit()

        df = pd.read_excel(file_path)

        suppliers = []
        for _, row in df.iterrows():
            supplier = Supplier(
                uuid=row.get("uuid", str(uuid.uuid4())),
                name=row["name"],
                description=row.get("description", "No description"),
                street=row.get("street"),
                city=row.get("city"),
                postal_code=row.get("postal_code"),
                house_number=row.get("house_number"),
                country=row.get("country")   
            )
            suppliers.append(supplier)

        self.session.add_all(suppliers)
        self.session.commit()
        print(f"Imported {len(suppliers)} suppliers successfully from {file_path}")
    
    def display_suppliers_table(self):
        from tabulate import tabulate
        import textwrap
        query="SELECT * FROM suppliers"
        suppliers_table = pd.read_sql_query(sql=query, con=self.engine)
        suppliers_table["house_number"] = suppliers_table["house_number"].astype(str)
        suppliers_table["postal_code"] = suppliers_table["postal_code"].astype(str)
        pd.set_option('display.max_columns', 7)
        pd.set_option('display.width', 200)
        print(tabulate(suppliers_table, headers='keys', tablefmt='github'))

    def add_sample_suppliers(self):
        from .models import Supplier
        siemens = Supplier(
            uuid=str(uuid.uuid4()),
            name="Siemens AG",
            description="Siemens AG is a global powerhouse focusing on the areas of electrification, automation, and digitalization. One of the world's largest producers of energy-efficient, resource-saving technologies",
            street="Werner-von-Siemens-Straße",
            house_number="1",
            postal_code="80333",
            city="Munich",
            country="Germany",
            date_created=datetime.utcnow(),
            date_modified=datetime.utcnow()
        )
        
        kuka = Supplier(
            uuid=str(uuid.uuid4()),
            name="KUKA AG",
            description="The KUKA Group is an internationally active automation group with revenue of approximately EUR 3.7 billion and approximately 15,000 employees. As one of the world's leading providers of intelligent, resource-efficient automation solutions, KUKA offers industrial robots, autonomous mobile robots (AMR) including controllers, software, and cloud-based digital services, as well as fully networked production systems for various industries and markets, such as automotive with a focus on e-mobility and batteries, electronics, metal and plastics, consumer goods, food, e-commerce, retail, and healthcare",
            street="Zugspitzstraße",
            house_number="140",
            postal_code="86165",
            city="Augsburg",
            country="Germany",
            date_created=datetime.utcnow(),
            date_modified=datetime.utcnow()
        )
        self.session.add(siemens)
        self.session.add(kuka)
        self.session.commit()
        print("Added sample suppliers: Siemens AG and KUKA AG")