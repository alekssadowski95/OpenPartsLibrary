# Getting Started

OpenPartsLibrary helps small engineering teams reuse known mechanical parts
instead of repeatedly searching supplier pages, old project folders, and CAD
downloads.

The normal local workflow is:

1. Install the Python dependencies.
2. Start the Flask web app or desktop wrapper.
3. Search the parts library for standard components.
4. Open a part page to inspect metadata, supplier data, CAD availability, and BOM usage.
5. Add useful parts to My Bill of Materials or open reusable BOM modules.
6. Download CAD packages and SPDX hardware BOM data for use in FreeCAD, procurement, or manufacturing handoff.

The app bootstraps itself from the bundled sample spreadsheet and CAD directory
when the runtime database is empty.
