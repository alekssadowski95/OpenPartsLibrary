import os
import pandas as pd
import uuid

from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Part, Supplier


# Initialize the parts library
pl = PartsLibrary()

# Clear the parts library
pl.delete_all()

# Create a new part
part_1 = Part(
            uuid = str(uuid.uuid4()),
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

# Create a new part
part_2 = Part(
            uuid = str(uuid.uuid4()),
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

# Create a new part
part_3 = Part(
            uuid = str(uuid.uuid4()),
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

# Add a all created parts to the parts library
pl.session.add(part_1)
pl.session.add(part_2)
pl.session.add(part_3)
pl.session.commit()

# Print the parts library in the terminal
pl.display_reduced()

supplier_1 = Supplier(

)



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
