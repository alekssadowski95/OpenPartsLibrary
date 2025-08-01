# OpenComponentLibrary
OpenComponentLibrary in Python

This table outlines the component metadata used in the OpenComponentLibrary.

| Property | Description |
|----------|-------------|
| `number` | Unique identifier for the component, often alphanumeric (e.g., `"MTR-12345"`). |
| `name` | Descriptive name of the component, typically used for display and search. |
| `description` | Detailed explanation of what the component is and its intended function. |
| `revision` | Version or iteration of the component (e.g., `"6"`). |
| `lifecycle_state` | Current status in the engineering lifecycle, like `"In Work"`, `"Released"`, `"Obsolete"`. |
| `owner` | Responsible person for the component. |
| `date_created` | Timestamp of when the component was first created in the system. |
| `date_modified` | Timestamp of the most recent update to the component. |
| `material` | The material from which the component is made (e.g., `"Aluminum 6061"`, `"ABS"`). |
| `mass` | Mass of the component, in kilograms. |
| `dimensions_x` | Length of the component along the X-axis, in millimeters. |
| `dimensions_y` | Width of the component along the Y-axis, in millimeters. |
| `dimensions_z` | Height of the component along the Z-axis, in millimeters. |
| `quantity` | Number of units of this component that are available. |
| `cad_file_reference` | Reference to the associated 3D CAD file (e.g. *.FCStd). |
| `attached_documents_reference` | References to external documents (e.g., datasheets, certifications). |
| `lead_time` | Expected procurement time, in days. |
| `make_or_buy` | Indicates whether the component is manufactured internally (`"Make"`) or externally sourced (`"Buy"`). |
| `supplier` | Preferred supplier or vendor name. |
| `manufacturer_number` | Vendor-specific identifier for the component, if purchased externally. |
| `unit_price` | Cost per individual unit of the component (e.g., `12.75`). |
| `currency` | Currency of the unit price (e.g., `EUR`). |


`id` and `uuid` will also be used internally, but database users does not have to worry about those.