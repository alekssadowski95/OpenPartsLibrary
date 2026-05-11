# App Overview

OpenPartsLibrary is organized around a small set of responsibilities.

- `openpartslibrary/__init__.py` creates and configures the Flask app.
- `openpartslibrary/models.py` defines SQLAlchemy tables for parts, files, suppliers, BOMs, and download events.
- `openpartslibrary/db.py` owns database setup and spreadsheet import/sync logic.
- `openpartslibrary/routes.py` registers public pages, JSON endpoints, downloads, thumbnails, and session BOM actions.
- `openpartslibrary/admin.py` registers Flask-Admin views and fallback admin pages.
- `openpartslibrary/boms.py` contains BOM creation, copying, flattening, cycle checks, numbering, and cost formatting.
- `openpartslibrary/search.py` normalizes search text, expands synonyms, and ranks component matches.
- `openpartslibrary/session_boms.py` stores temporary user-created BOMs as JSON files tied to the browser session.
- `openpartslibrary/downloads.py` brands filenames and records download analytics.
- `openpartslibrary/thumbnails.py` coordinates FreeCAD and Blender thumbnail generation.
- `openpartslibrary/hbom.py` exports selected parts as SPDX hardware BOM JSON-LD.
- `openpartslibrary/templates/` contains Jinja templates for the public and admin UI.

## Runtime Flow

On startup, the app configures writable data folders, migrates older SQLite
schemas, creates tables, imports sample data when needed, syncs CAD files, and
creates part-wrapper BOMs for every component.

Public routes then use a shared SQLAlchemy session to render searchable pages,
component details, BOM views, downloads, and user-session BOMs.

## Data Model

Components are the central records.  A component can have one CAD file, multiple
supporting files, one supplier, and parent/child component relationships.

Bill of materials records form reusable assembly trees.  A normal BOM represents
an assembly or reusable module.  A part-wrapper BOM represents exactly one
component, which lets BOM trees mix assemblies and individual parts using one
relationship model.
