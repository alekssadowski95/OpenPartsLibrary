import os
import pandas as pd
import uuid

from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Part, Supplier, File


# Initialize the parts library
pl = PartsLibrary()

# Clear the parts library
pl.delete_all()

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
            currency='EUR'
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
            currency='EUR'
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
            currency='EUR'
)

# Load file and original name, change name to uuid and save it in the data/files dir
# ..
file_1_path = ''
file_1_uuid = str(uuid.uuid4())
file_1_name = 'screw.FCStd'
# Create a new file
file_1 = File(uuid = file_1_uuid, name = file_1_name, description = 'This is a CAD file.')
# Assign file to part cad reference
part_1.cad_reference.append(file_1)

# Load file and original name, change name to uuid and save it in the data/files dir
# ..
file_2_path = ''
file_2_uuid = str(uuid.uuid4())
file_2_name = 'screw.FCStd'
# Create a new file
file_2 = File(uuid = file_2_uuid, name = file_2_name, description = 'This is a CAD file.')
# Assign file to part cad reference
part_2.cad_reference.append(file_2)

# Load file and original name, change name to uuid and save it in the data/files dir
# ..
file_3_path = ''
file_3_uuid = str(uuid.uuid4())
file_3_name = 'screw.FCStd'
# Create a new file
file_3 = File(uuid = file_3_uuid, name = file_3_name, description = 'This is a CAD file.')
# Assign file to part cad reference
part_3.cad_reference.append(file_3)

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

# Add a all created parts to the parts library
pl.session.add(supplier_1)
pl.session.add(supplier_2)
supplier_1.parts.append(part_1)
supplier_1.parts.append(part_2)
supplier_2.parts.append(part_3)
pl.session.commit()

# Prints the parts, suppliers and files tables in the terminal
pl.display()

'''
# Get the total value all parts in the library
print('Total value of all parts in the library: ' + str(pl.total_value()) + ' EUR')

# Load the part with number 'SCRW-1002'
part = pl.session.query(Part).filter(Part.number == 'SCRW-1002').first()
print(part)

# Update the quantity on the part with number 'SCRW-2001' by lowering by 10
part = pl.session.query(Part).filter(Part.number == 'SCRW-2001').first()
part.quantity -= 10
pl.session.commit()
pl.display_reduced()
print('Total value of all parts in the library: ' + str(pl.total_value()) + ' EUR')

# Delete the part with number 'SCRW-1003' from the database
part = pl.session.query(Part).filter(Part.number == 'SCRW-1003').delete()
pl.session.commit()
pl.display_reduced()

# Displaying the highest unit price parts
highest_price_parts = pl.session.query(Part).order_by(Part.unit_price.desc()).limit(5).all()
print("\nTop 5 Part with the highest unit price:")
for part in highest_price_parts:
    print(f"Number: {part.number}, Name: {part.name}, Unit Price: {part.unit_price} {part.currency}")


# Displaying Supplier table contents
pl.add_sample_suppliers()
pl.display_suppliers()
'''
