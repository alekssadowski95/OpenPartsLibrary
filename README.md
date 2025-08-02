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

print_parts(session)
```

This will give you the following output, loading all the integrated parts of the library:
<div style="background-color: rgb(50, 50, 50); color: white;"> 
```console
    id                                  uuid       number                       name  ... supplier manufacturer_number unit_price currency
0    1  1c0e85cd-73b7-4af3-9ccc-ae17d140c438  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
1    2  a8d2fa31-47e7-4fc0-b1a8-0df2079ff407  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
2    3  e2614ac3-4a17-464c-9fd7-c452fed55c03  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
3    4  058be9dc-54ca-434e-849f-07e6b49902c2  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
4    5  afc48527-c3a2-4be1-bd0e-06ba15a18dd8  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
5    6  262e3d32-9de6-4300-83cf-3aeba6bd7f40  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
6    7  aee95646-61a1-4ef7-b530-97fef65a5263  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
7    8  f839cc56-a3b8-4629-b18f-81c6b6a1a5e2  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
8    9  0ca04d9d-189a-4119-bf0b-510103b084ca  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
9   10  029bdd52-96d0-4488-9d25-dd95c459eadc  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
10  11  a4f55685-4d43-4093-aa9f-49dfb0d4cc5b  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
11  12  51b15d47-96b1-44b7-97ea-5a9790b5aef1  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
12  13  09fc376c-6740-405e-9a7b-c0502ac9b243  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
13  14  0d3b7791-63ec-463a-b66e-6fc1134a3f5f  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
14  15  78cdee85-0779-4a4d-b3a4-5104dcf35ad3  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
15  16  79662a17-c825-44bd-a20a-2b13580e47a6  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
16  17  dccd8e60-04ac-4c7f-8a46-0f391be4854d  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None
17  18  9d6a9432-c8e4-412b-9333-872b81e2571c  TRX-230-115  Trochoidal milling cutter  ...     None                None       None     None

[18 rows x 24 columns]
```
</div>

## Modifying the parts library

Adding a new part to the library:

```python 
from openpartslibrary.models import Part

part_1 = Part(name='Trochoidal milling cutter', number='TRX-230-100')
session.add(part_1)
session.commit()

print_parts(session)
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