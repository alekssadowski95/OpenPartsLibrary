<img src="./openpartslibrary/images/database.png" width="128" alt="OpenPartsLibrary logo"></img>
# OpenPartsLibrary
**OpenPartsLibrary** is a Python library designed to serve as a centralized parts database for Bill of Materials (BOM), Product Data Management (PDM), and Product Lifecycle Management (PLM) systems. It provides structured data models and APIs for managing components, part metadata, sourcing, and lifecycle states. OpenPartsLibrary streamlines integration with engineering workflows, enabling consistent part usage and traceability across design and manufacturing processes.

## Quickstart

Install the openpartslibrary via pip
```console
pip install OpenPartsLibrary
```

A minimal OpenPartsLibrary application looks something like this:
```python 
from openpartslibrary.db import PartsLibrary

pl = PartsLibrary()

pl.display()
```

This will give you the following output, loading all the integrated parts of the library:
```console
      id                              uuid     number               name  ...                supplier manufacturer_number unit_price currency
0      1  7dd559e06e1044c9b66e4a61df1072b6  SCRW-1000   Screw Type A 5mm  ...          Acme Fasteners          MFG-625535       0.86      EUR
1      2  ced16afd527e483db362f44d6fcedd82  SCRW-1001   Screw Type A 5mm  ...  In-House Manufacturing          MFG-807818       4.02      EUR
2      3  e3f8a20ab4974e45bca023a31c50e862  SCRW-1002   Screw Type C 2mm  ...   Precision Screws Ltd.          MFG-543204       4.13      EUR
3      4  7115fbc429594f09881181a3503b62db  SCRW-1003   Screw Type B 3mm  ...  In-House Manufacturing          MFG-916662       3.52      EUR
4      5  8381dfa595854aa78b9d373d8a3f3f63  SCRW-1004   Screw Type A 1mm  ...  In-House Manufacturing          MFG-742978       0.38      EUR
..   ...                               ...        ...                ...  ...                     ...                 ...        ...      ...
115  116  67f3f0ec88974cdc8e9ac4eea5cf1351  SCRW-1115   Screw Type B 1mm  ...  In-House Manufacturing          MFG-406022       3.95      EUR
116  117  a685e7b7135f48579a34ca45cf6baafe  SCRW-1116  Screw Type B 10mm  ...  In-House Manufacturing          MFG-230904       2.99      EUR
117  118  c5c256a8a8b04972ab87ef84110f7d5a  SCRW-1117   Screw Type A 4mm  ...                  BoltCo          MFG-343539       0.23      EUR
118  119  2b9eda46cb8b45e093c084a437f01ba2  SCRW-1118   Screw Type B 1mm  ...   Precision Screws Ltd.          MFG-247256       4.28      EUR
119  120  39a71a5ed7224ee0bf5e919870ebe0a3  SCRW-1119   Screw Type D 4mm  ...                 HexTech          MFG-293100       2.06      EUR

[120 rows x 24 columns]
```

## Working with the parts library

Creating a new part in the library:
```python 
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
```

Loading a part from the library:
```python 
part = pl.session.query(Part).filter(Part.number == 'SCRW-1002').first()
print(part)
```

Modifying a part from the library:
```python 
part = pl.session.query(Part).filter(Part.number == 'SCRW-2001').first()
part.quantity -= 10
pl.session.commit()
pl.display_reduced()
```

Deleting a part from the library:
```python 
part = pl.session.query(Part).filter(Part.number == 'SCRW-1003').delete()
pl.session.commit()
pl.display_reduced()
```

Getting the total value of all parts in the library:
```python 
print('Total value of all parts in the library: ' + str(pl.total_value()) + ' EUR')
```

Creating parts from a parts list in a Excel-spreadsheet (*.xlsx). Take note, that the spreadsheet needs to implement the schema specified in this repository:
```python 
pl.create_parts_from_spreadsheet('C:/Users/Work/Documents/Github/OpenPartsLibrary/openpartslibrary/sample/parts_data_sample.xlsx')
```

## Part schema
This table outlines the `Part` properties used in the OpenPartsLibrary.

| Property | Description |
|----------|-------------|
| `number` | Unique identifier for the part, often alphanumeric (e.g., `"MTR-12345"`). |
| `name` | Descriptive name of the part, typically used for display and search. |
| `description` | Detailed explanation of what the part is and its intended function. |
| `revision` | Version or iteration of the part (e.g., `"6"`). |
| `lifecycle_state` | Current status in the engineering lifecycle, like `"In Work"`, `"Released"`, `"Obsolete"`. |
| `owner` | Responsible person for the part. |
| `date_created` | Timestamp of when the part was first created in the system. |
| `date_modified` | Timestamp of the most recent update to the part. |
| `material` | The material from which the part is made (e.g., `"Aluminum 6061"`, `"ABS"`). |
| `mass` | Mass of the part, in kilograms. |
| `dimensions_x` | Length of the part along the X-axis, in millimeters. |
| `dimensions_y` | Width of the part along the Y-axis, in millimeters. |
| `dimensions_z` | Height of the part along the Z-axis, in millimeters. |
| `quantity` | Number of units of this part that are available. |
| `cad_file_reference` | Reference to the associated 3D CAD file (e.g. *.FCStd). |
| `attached_documents_reference` | References to external documents (e.g., datasheets, certifications). |
| `lead_time` | Expected procurement time, in days. |
| `make_or_buy` | Indicates whether the part is manufactured internally (`"Make"`) or externally sourced (`"Buy"`). |
| `supplier` | Preferred supplier or vendor name. |
| `manufacturer_number` | Vendor-specific identifier for the part, if purchased externally. |
| `unit_price` | Cost per individual unit of the part (e.g., `12.75`). |
| `currency` | Currency of the unit price (e.g., `EUR`). |


`id` and `uuid` will also be used internally, but database users does not have to worry about those.

Credits:
icon: <a href="https://www.flaticon.com/free-icons/database" title="database icons">Database icons created by Smashicons - Flaticon</a>