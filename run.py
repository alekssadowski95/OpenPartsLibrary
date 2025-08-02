from openpartslibrary.db import PartsLibrary

# Initialize the parts library
pl = PartsLibrary()
pl.display()

# Clear library and load new parts from spreadsheet
import os

pl.delete_all()
sample_path = os.path.join(os.path.dirname(__file__), 'openpartslibrary', 'sample', 'parts_data_sample.xlsx') 
pl.create_parts_from_spreadsheet(sample_path)
pl.display()

# Create a new single part and add it to the database
from openpartslibrary.models import Part

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
pl.session.add(new_part)
pl.session.commit()
pl.display_reduced()

# Update the quantity on the part with number 'SCRW-1002' by lowering by 10
part = pl.session.query(Part).filter(Part.number == 'SCRW-2001').first()
part.quantity -= 10
pl.session.commit()
pl.display_reduced()

# Get the total value all parts in the library
print('Total value of all parts in the library: ' + str(pl.total_value()) + ' EUR')