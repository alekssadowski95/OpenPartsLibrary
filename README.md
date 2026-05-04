# OpenPartsLibrary

OpenPartsLibrary helps hardware startups and small manufacturing teams develop machines faster by reusing cheap standard components from AliExpress.com together with ready-to-use CAD files.

The focus is practical mechanical engineering: find a standard part, preview or download its CAD model, use it in a FreeCAD assembly, and keep track of how that part is used across bills of materials.

## Purpose

Early-stage machine development is often slowed down by repeated component searches, missing CAD files, inconsistent part names, and unclear reuse across assemblies.

OpenPartsLibrary provides a focused part library for this workflow:

- Search standard mechanical parts by engineering terms, supplier names, part numbers, and dimensions.
- Reuse provided CAD files directly in machine assemblies.
- Prioritize practical size matches, such as the next larger rail length for a requested dimension.
- Collect parts into My Bill of Materials for download and handoff.
- Look up which BOMs already use a specific part.
- Download CAD files and a structured hardware BOM package.

## Search

Search is tuned for mechanical part discovery. It supports synonyms such as `guide`, `rail`, and `linear guide`, and it treats numeric input as a specification instead of plain text.

For the end user, this means searches return practical engineering matches instead of only literal text matches. If a requested size is not available, the closest usable standard part can appear first.

## Reusable BOM Modules

Precreated BOMs represent frequently combined parts that are often reused as machine modules.

Examples include complete linear axes, rail sets, motor and bracket combinations, or other groups of components that are usually selected together.

Instead of collecting every rail, carriage, motor, fastener, and mounting bracket one by one, engineers can start from an existing BOM that already reflects a proven combination.

The app also shows where a specific part is used across BOMs. This helps engineers understand which modules depend on a part and makes reuse more transparent when preparing or changing FreeCAD assemblies.

## My Bill Of Materials

Selected parts are collected in My Bill of Materials. From there, users can review quantities, estimated cost, CAD availability, and download the package.

## FreeCAD Assembly Focus

The library is intended for assemblies created with FreeCAD.

Many low-cost components from AliExpress are usable for prototypes, fixtures, automation equipment, test rigs, and early production machines, but the engineering work becomes slow when CAD models and part information are scattered.

OpenPartsLibrary keeps the reusable part data close to the CAD workflow, so engineers can quickly insert known components into assemblies instead of rebuilding or searching for the same models again.

Typical part families include:

- Linear rails and sliding blocks
- Aluminum profiles and brackets
- Fasteners, nuts, washers, and spacers
- Plates, panels, adapters, and mounting parts
- Other purchased standard components used in machine frames and mechanisms

## Running Locally

Install dependencies:

```console
pip install -r requirements.txt
```

Run the web app:

```console
python app.py
```

Open:

```text
http://localhost:5000
```

Desktop wrapper:

```console
python run_desktop.py
```

Runtime data is stored in:

```text
instance/data/
```

## How To Contribute

This section is for software developers and technical contributors.

Useful project areas:

```text
openpartslibrary/search.py     Search scoring and ranking
openpartslibrary/routes.py     Public app routes
openpartslibrary/templates/    User interface templates
openpartslibrary/hbom.py       Hardware BOM export
openpartslibrary/models.py     Data models
openpartslibrary/admin.py      Admin and BOM management views
```

Keep contributions focused on the engineering workflow: faster part reuse, better CAD/BOM handling, and clearer support for FreeCAD-based machine assemblies.

## License

OpenPartsLibrary is provided under the license included in this repository.
