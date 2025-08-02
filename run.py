from openpartslibrary.db import PartsLibrary

# Initialize the parts library
pl = PartsLibrary()
pl.display()

# Clear library and load new parts from spreadsheet
pl.delete_all()
import os
sample_path = os.path.join(os.path.dirname(__file__), 'openpartslibrary', 'sample', 'parts_data_sample.xlsx') 
pl.create_parts_from_spreadsheet(sample_path)
pl.display()

