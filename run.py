from openpartslibrary.db import PartsLibrary

# Initialize the parts library
pl = PartsLibrary()
pl.display()

# Clear library and load new parts from spreadsheet
import os
import pandas as pd
import uuid

pl.delete_all()
sample_path = os.path.join(os.path.dirname(__file__), 'openpartslibrary', 'sample', 'parts_data_sample.xlsx') 
pl.create_parts_from_spreadsheet(sample_path)
pl.display()

# Create a new single part and add it to the database
from openpartslibrary.models import Part, Supplier

new_part = Part(
            number='SCRW-2001',
            name='Screw Type Z (Special) M5x14',
            description='A special kind of screw for safety switches',
            revision="1",
            lifecycle_state="In Work",
            owner='Max Mustermann',
            material='Steel',
            mass=0.03,
            dimension_x=0.02,
            dimension_y=0.005,
            dimension_z=0.005,
            quantity=100,
            cad_reference='CAD REFERENCE',
            attached_documents_reference='DOCUMENTS REFERENCE',
            lead_time=10,
            make_or_buy='make',
            supplier='In-House Manufacturing',
            manufacturer_number='MFN-100001',
            unit_price=0.45,
            currency='EUR'
        )
#Add 3 more parts
new_part2 = Part(
            uuid=str(uuid.uuid4()),
            number='BOLT-2002',
            name='Hex Bolt',
            description='A standard hex bolt',
            revision="1",
            lifecycle_state="In Work",
            owner="Portland Bolt",
            material='Stainless Steel',
            mass=0.05,
            dimension_x=0.03,
            dimension_y=0.01,
            dimension_z=0.01,
            quantity=150,
            cad_reference='CAD REFERENCE BOLT',
            attached_documents_reference='DOCUMENTS REFERENCE BOLT',
            lead_time=7,    
            make_or_buy='buy',
            supplier='Portland Bolt',
            manufacturer_number='PB-2002',
            unit_price=0.75,    
            currency='EUR'
        )
new_part3 = Part(
            uuid=str(uuid.uuid4()),
            number='BOLT-2003',
            name='Carriage Bolt',
            description='A standard carriage bolt',
            revision="1",
            lifecycle_state="In Work",
            owner="Fastenal",
            material='Carbon Steel',
            mass=0.04,
            dimension_x=0.025,
            dimension_y=0.008,
            dimension_z=0.008,
            quantity=200,
            cad_reference='CAD REFERENCE CARRIAGE BOLT',
            attached_documents_reference='DOCUMENTS REFERENCE CARRIAGE BOLT',
            lead_time=5,
            make_or_buy='buy',
            supplier='Fastenal',
            manufacturer_number='FB-3003',
            unit_price=0.60,
            currency='EUR'
)
new_part4 = Part(
            uuid=str(uuid.uuid4()),
            number='NUT-2004',
            name='Hex Nut',     
            description='A standard hex nut',
            revision="1",
            lifecycle_state="In Work",
            owner="Grainger",
            material='Brass',
            mass=0.02,
            dimension_x=0.015,
            dimension_y=0.007,
            dimension_z=0.007,
            quantity=300,
            cad_reference='CAD REFERENCE HEX NUT',
            attached_documents_reference='DOCUMENTS REFERENCE HEX NUT',
            lead_time=4,
            make_or_buy='buy',
            supplier='Grainger',
            manufacturer_number='GN-4004',
            unit_price=0.30,
            currency='EUR'
)

pl.session.add(new_part)
pl.session.add(new_part2)
pl.session.add(new_part3)
pl.session.add(new_part4)
pl.session.commit()
pl.display_reduced()

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

