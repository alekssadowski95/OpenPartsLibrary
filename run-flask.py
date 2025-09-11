import os
import uuid

from flask import Flask
from flask import render_template

from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Part, Supplier, File, Component, ComponentComponent


# Create the flask app instance
app = Flask(__name__)

# Define the path for the app
app.config['APP_PATH'] = os.path.dirname(os.path.abspath(__file__))

# Add secret key
app.config['SECRET_KEY'] = 'afs87fas7bfsa98fbasbas98fh78oizu'

# Get the paths for this project
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DATA_DIR = os.path.join(PROJECT_DIR, "openpartslibrary", "sample")
EXPORT_DIR = os.path.join(PROJECT_DIR, "openpartslibrary", "export")
LIBRARY_DATA_DIR = os.path.join(PROJECT_DIR, "openpartslibrary", "data")
LIBRARY_DATA_FILES_DIR = os.path.join(LIBRARY_DATA_DIR, "files")

# Initialize the parts library
db_path = os.path.join(app.static_folder, 'parts.db')
pl = PartsLibrary(db_path = db_path)


''' Routes
'''
@app.route('/')
def index():
    # Clear the parts library
    pl.delete_all()

    # Load file and original name, change name to uuid and save it in the data/files dir
    # ..
    file_1_path = os.path.join(SAMPLE_DATA_DIR, 'M6x12-Screw.FCStd')
    file_1_uuid = str(uuid.uuid4())
    file_1_name = os.path.basename(file_1_path)
    file_1_ext = os.path.splitext(file_1_path)[1]  # includes the dot
    with open(file_1_path, "rb") as src_file:   # read in binary mode
        data = src_file.read()
        dst_path = os.path.join(LIBRARY_DATA_FILES_DIR, file_1_uuid + file_1_ext)
        with open(dst_path, "wb") as dst_file:   # write in binary mode
            dst_file.write(data)
    # Create a new file
    file_1 = File(uuid = file_1_uuid, name = file_1_name, description = 'This is a CAD file.')

    # Load file and original name, change name to uuid and save it in the data/files dir
    # ..
    file_2_path = os.path.join(SAMPLE_DATA_DIR, 'M6x20-Screw.FCStd')
    file_2_uuid = str(uuid.uuid4())
    file_2_name = os.path.basename(file_2_path)
    file_2_ext = os.path.splitext(file_2_path)[1]  # includes the dot
    with open(file_2_path, "rb") as src_file:   # read in binary mode
        data = src_file.read()
        dst_path = os.path.join(LIBRARY_DATA_FILES_DIR, file_2_uuid + file_2_ext)
        with open(dst_path, "wb") as dst_file:   # write in binary mode
            dst_file.write(data)
    # Create a new file
    file_2 = File(uuid = file_2_uuid, name = file_2_name, description = 'This is a CAD file.')

    # Load file and original name, change name to uuid and save it in the data/files dir
    # ..
    file_3_path = os.path.join(SAMPLE_DATA_DIR, 'M6x35-Screw.FCStd')
    file_3_uuid = str(uuid.uuid4())
    file_3_name = os.path.basename(file_3_path)
    file_3_ext = os.path.splitext(file_3_path)[1]  # includes the dot
    with open(file_3_path, "rb") as src_file:   # read in binary mode
        data = src_file.read()
        dst_path = os.path.join(LIBRARY_DATA_FILES_DIR, file_3_uuid + file_3_ext)
        with open(dst_path, "wb") as dst_file:   # write in binary mode
            dst_file.write(data)
    # Create a new file
    file_3 = File(uuid = file_3_uuid, name = file_3_name, description = 'This is a CAD file.')

    # Create a new part
    part_1 = Part(
                uuid = str(uuid.uuid4()),
                number='SCRW-2001',
                name='Screw ISO 4762 M6x12',
                description='A hexagon socket head cap screw for fastening metal parts',
                revision="1",
                lifecycle_state="In Work",
                owner='Max Mustermann',
                material='Steel',
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
                cad_reference = file_1
    )

    # Create a new part
    part_2 = Part(
                uuid = str(uuid.uuid4()),
                number='SCRW-2002',
                name='Screw ISO 4762 M6x20',
                description='A hexagon socket head cap screw for fastening metal parts',
                revision="1",
                lifecycle_state="In Work",
                owner="Portland Bolt",
                material='Stainless Steel',
                mass=0.05,
                dimension_x=0.03,
                dimension_y=0.01,
                dimension_z=0.01,
                quantity=150,
                attached_documents_reference='DOCUMENTS REFERENCE BOLT',
                lead_time=7,    
                make_or_buy='buy',
                manufacturer_number='PB-2002',
                unit_price=0.15,    
                currency='EUR',
                cad_reference = file_2
    )

    # Create a new part
    part_3 = Part(
                uuid = str(uuid.uuid4()),
                number='SCRW-2003',
                name='Screw ISO 4762 M6x35',
                description='A hexagon socket head cap screw for fastening metal parts',
                revision="1",
                lifecycle_state="In Work",
                owner="Grainger",
                material='Brass',
                mass=0.02,
                dimension_x=0.015,
                dimension_y=0.007,
                dimension_z=0.007,
                quantity=300,
                attached_documents_reference='DOCUMENTS REFERENCE HEX NUT',
                lead_time=4,
                make_or_buy='buy',
                manufacturer_number='GN-4004',
                unit_price=0.18,
                currency='EUR',
                cad_reference = file_3
    )

    # Add a all created parts to the parts library
    pl.session.add(part_1)
    pl.session.add(part_2)
    pl.session.add(part_3)
    pl.session.commit()

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

    # Add a all created parts to the parts library
    pl.session.add(supplier_1)
    pl.session.add(supplier_2)
    pl.session.add(supplier_3)
    pl.session.add(supplier_4)
    supplier_1.parts.append(part_1)
    supplier_1.parts.append(part_2)
    supplier_2.parts.append(part_3)
    pl.session.commit()

    # Create a new component and add it to the library
    component_1 = Component(uuid = str(uuid.uuid4()), part = part_1, name = part_1.name)
    component_2 = Component(uuid = str(uuid.uuid4()), part = part_2, name = part_2.name)
    component_3 = Component(uuid = str(uuid.uuid4()), part = part_3, name = part_3.name)
    component_4 = Component(uuid = str(uuid.uuid4()), name = 'Screw assembly')
    pl.session.add(component_1)
    pl.session.add(component_2)
    pl.session.add(component_3)
    pl.session.add(component_4)
    pl.session.commit()

    component_4.children.append(component_1)
    component_4.children.append(component_2)
    component_4.children.append(component_3)
    pl.session.commit()

    components_components = pl.session.query(ComponentComponent).all()
    components = pl.session.query(Component).all()
    parts = pl.session.query(Part).all()
    suppliers = pl.session.query(Supplier).all()
    files = pl.session.query(File).all()
    
    return render_template('home.html', components_components = components_components, components = components, parts = parts, suppliers = suppliers, files = files)


if __name__ == '__main__':
    app.run(host="localhost", port=5000, debug=True)