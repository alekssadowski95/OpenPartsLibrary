# OpenPartsLibrary
**OpenPartsLibrary** is a Python library designed to serve as a centralized parts database for Bill of Materials (BOM), Product Data Management (PDM), and Product Lifecycle Management (PLM) systems. It provides structured data models and APIs for managing components, part metadata, sourcing, and lifecycle states. OpenPartsLibrary streamlines integration with engineering workflows, enabling consistent part usage and traceability across design and manufacturing processes.

## Quickstart

Install the openpartslibrary via pip

```console
pip install openpartslibrary
```

A minimal OpenPartsLibrary application looks something like this:

```python 
from openpartslibrary.db import create_session

session = create_session()

print_all_parts(session)
```

Adding a new part to the library:

```python 
from openpartslibrary.models import Part

part_1 = Part(name='Trochoidal milling cutter', number='TRX-230-100')
session.add(part_1)
session.commit()

print_all_parts(session)
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