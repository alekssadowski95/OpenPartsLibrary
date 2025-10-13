from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import pandas as pd

from datetime import datetime

from .models import Base, Part, Supplier, File, Component, ComponentComponent, Material

import uuid

import os


class PartsLibrary:
    def __init__(self, db_path = None, data_dir_path = None):
        # Set database path
        if db_path is not None:
            self.db_path = db_path
        else:
            self.db_path = os.path.join(os.path.dirname(__file__), 'data', 'parts.db') 
        
        # Initialize the database and its connection 
        self.engine = create_engine('sqlite:///' + self.db_path)
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.session = self.session_factory()

        # Set reference files directory path
        if data_dir_path is not None:
            self.data_dir_path = data_dir_path
        else:
            self.data_dir_path = os.path.join(os.path.dirname(__file__), 'data') 
        
        self.data_cad_dir_path = os.path.join(self.data_dir_path, "cad")
        self.data_files_dir_path = os.path.join(self.data_dir_path, "files")

        self.sample_data_dir_path = os.path.join(os.path.dirname(__file__), 'sample') 


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
        
        for filename in os.listdir(self.data_cad_dir_path):
            filepath = os.path.join(self.data_cad_dir_path, filename)
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

    def add_sample_data(self):
        # Create a new supplier
        supplier_1 = Supplier(
                        uuid = str(uuid.uuid4()),
                        name = 'Adolf Würth GmbH & Co. KG',
                        description = 'The Würth Group is a leader in the development, manufacture, and distribution of assembly and fastening materials. The globally active family-owned company, headquartered in Künzelsau, Germany, comprises over 400 subsidiaries with over 2,800 branches in 80 countries.',
                        street = 'Reinhold-Würth-Straße',
                        house_number = '12',
                        postal_code = '74653',
                        city = 'Künzelsau-Gaisbach',
                        country = 'Deutschland'
        )

        # Create a new supplier
        supplier_2 = Supplier(
                        uuid = str(uuid.uuid4()),
                        name = 'Robert Bosch GmbH',
                        description = 'The Bosch Group is a leading international supplier of technology and services with approximately 418,000 associates worldwide (as of December 31, 2024).',                        
                        street = 'Robert-Bosch-Platz',
                        house_number = '1',
                        postal_code = '70839',
                        city = 'Gerlingen-Schillerhöhe',
                        country = 'Deutschland'
        )

        # Create a new supplier
        supplier_3 = Supplier(
                        uuid = str(uuid.uuid4()),
                        name = 'ALSADO Inh. Aleksander Sadowski',
                        description = 'ALSADO is a small company in Sankt Augustin in Germany, which specializes in CAD and PDM/PLM software development. Recetnly ALSADO is also entering the hardward manufacturing market with its innovative fastening solution for safery applications.',                        
                        street = 'Liebfrauenstraße',
                        house_number = '31',
                        postal_code = '53757',
                        city = 'Sankt Augustin',
                        country = 'Deutschland'
        )

        # Create a new supplier
        supplier_4 = Supplier(
                        uuid = str(uuid.uuid4()),
                        name = 'Xometry Europe GmbH ',
                        description = 'Xometry’s (NASDAQ: XMTR) AI-powered marketplace and suite of cloud-based services are rapidly digitising the manufacturing industry.',                        
                        street = 'Ada-Lovelace-Straße',
                        house_number = '9',
                        postal_code = '85521',
                        city = 'Ottobrunn',
                        country = 'Deutschland'
        )

        self.session.add(supplier_1)
        self.session.add(supplier_2)
        self.session.add(supplier_3)
        self.session.add(supplier_4)
        self.session.commit()

        fcstd_file_names = [
            ('M6x8-Screw.FCStd', str(uuid.uuid4())),
            ('M6x12-Screw.FCStd', str(uuid.uuid4())),
            ('M6x14-Screw.FCStd', str(uuid.uuid4())),
            ('M6x16-Screw.FCStd', str(uuid.uuid4())),
            ('M6x20-Screw.FCStd', str(uuid.uuid4())),
            ('M6x25-Screw.FCStd', str(uuid.uuid4())),
            ('M6x30-Screw.FCStd', str(uuid.uuid4())),
            ('M6x35-Screw.FCStd', str(uuid.uuid4())),
            ('M6x40-Screw.FCStd', str(uuid.uuid4())),
            ('M6x45-Screw.FCStd', str(uuid.uuid4())),
            ('M6x50-Screw.FCStd', str(uuid.uuid4())),
            ('M6x55-Screw.FCStd', str(uuid.uuid4())),
            ('M6x60-Screw.FCStd', str(uuid.uuid4())),
            ('M6x65-Screw.FCStd', str(uuid.uuid4())),
            ('M6x70-Screw.FCStd', str(uuid.uuid4())),
            ('M6x75-Screw.FCStd', str(uuid.uuid4())),
            ('M6x80-Screw.FCStd', str(uuid.uuid4())),
            ('M6x85-Screw.FCStd', str(uuid.uuid4())),
            ('M6x90-Screw.FCStd', str(uuid.uuid4()))
        ]
        
        part_number = 200001
        for fcstd_file_name in fcstd_file_names:
            # Load file and original name, change name to uuid and save it in the data/files dir
            # ..
            file_path = os.path.join(self.sample_data_dir_path, fcstd_file_name[0])
            file_uuid = fcstd_file_name[1]
            file_name = os.path.basename(file_path)
            file_ext = os.path.splitext(file_path)[1]  # includes the dot
            with open(file_path, "rb") as src_file:   # read in binary mode
                data = src_file.read()
                dst_path = os.path.join(self.data_cad_dir_path, file_uuid + file_ext)
                with open(dst_path, "wb") as dst_file:   # write in binary mode
                    dst_file.write(data)
            
            # Create a new file
            cad_file = File(uuid = file_uuid, name = file_name, description = 'This is a CAD file.')
            self.session.add(cad_file)
            self.session.commit()

            part = Part(
                    uuid = str(uuid.uuid4()),
                    number='SUP-' + str(part_number),
                    name='Screw ISO 4762 ' + os.path.splitext(file_name)[0],
                    description='A hexagon socket head cap screw for fastening metal parts',
                    revision="1",
                    lifecycle_state="In Work",
                    owner='Max Mustermann',
                    material='Stainless Steel',
                    mass=0.03,
                    dimension_x=0.02,
                    dimension_y=0.005,
                    dimension_z=0.005,
                    quantity=100,
                    attached_documents_reference='DOCUMENTS REFERENCE',
                    lead_time=10,
                    make_or_buy='make',
                    manufacturer_number='MFN-100001',
                    unit_price=0.10,
                    currency='EUR',
                    cad_file=cad_file,
            )
            self.session.add(part)
            self.session.commit()

            supplier_1.parts.append(part)
            self.session.commit()

            component = Component(uuid = str(uuid.uuid4()), part = part, name = part.name)
            self.session.add(component)
            self.session.commit()

            part_number = part_number + 1
      

        component_5 = Component(uuid = str(uuid.uuid4()), name = 'Screw assembly')
        self.session.add(component)
        self.session.commit()

        component_5.children.append(self.session.query(Component).filter_by(id = 1).first())
        component_5.children.append(self.session.query(Component).filter_by(id = 2).first())
        component_5.children.append(self.session.query(Component).filter_by(id = 3).first())
        component_5.children.append(self.session.query(Component).filter_by(id = 4).first())
        self.session.commit()

def add_sample_materials(self):
    # Adding sample materials
    material_name = "Steel AISI 1020"
    existing_material = self.session.query(Material).filter_by(name=material_name).first()
    if not existing_material:
        material_steel_1020 = Material(
            uuid = str(uuid.uuid4()),
            name = "Steel AISI 1020",
            category="Metal",
            density=7850,
            youngs_modulus=2.1e11,
            poisson_ratio=0.29,
            yield_strength=3.5e8,
            ultimate_strength=4.2e8,
            thermal_conductivity=51,
            specific_heat=486,
            thermal_expansion=1.2e-5
        )
        self.session.add(material_steel_1020)
        self.session.commit()
    else:
        print(f"Material '{material_name}' already exists. Skipping addition.")

def add_material(self, name, category, density, youngs_modulus, poisson_ratio, yield_strength, ultimate_strength, thermal_conductivity, specific_heat, thermal_expansion):
        material = Material(
            uuid = str(uuid.uuid4()),
            name = name,
            category = category,
            density = density,
            youngs_modulus = youngs_modulus,
            poisson_ratio = poisson_ratio,
            yield_strength = yield_strength,
            ultimate_strength = ultimate_strength,
            thermal_conductivity = thermal_conductivity,
            specific_heat = specific_heat,
            thermal_expansion = thermal_expansion
        )
        self.session.add(material)
        self.session.commit()
        print(f"Material '{name}' added successfully.")
