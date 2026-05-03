# OpenPartsLibrary

OpenPartsLibrary is a small Flask application and Python data layer for browsing a hardware component library, previewing CAD files, collecting parts into a selection, and downloading selected CAD files with a SPDX 3.x hardware BOM.

The public app is intentionally simple: component list, component detail, CAD preview, file detail, parts selection, and tracked downloads. Data management is handled through Flask-Admin when `Flask-Admin` is installed.

## Quickstart

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

Run the desktop wrapper:

```console
python run_desktop.py
```

## Data Location

Runtime data lives outside the Python package:

```text
instance/data/
```

That folder contains the SQLite database and uploaded or copied CAD/files:

```text
instance/data/parts.db
instance/data/cad/
instance/data/files/
```

You can override the data location with:

```console
set OPENPARTSLIBRARY_DATA_DIR=C:\path\to\data
```

On Linux/macOS:

```console
export OPENPARTSLIBRARY_DATA_DIR=/path/to/data
```

If the database is empty, the app imports the bundled sample spreadsheet from:

```text
openpartslibrary/sample/components.ods
```

## Admin

When `Flask-Admin` is installed, the app exposes:

```text
/admin/
```

The admin area manages components, files, suppliers, materials, component relationships, and download events.

## Downloads

Individual component CAD downloads are tracked in the `download_events` table.

Selection downloads create a ZIP containing:

- CAD files for the selected components
- `hardware-bom_OpenPartsLibrary.spdx.jsonld`

Downloaded filenames receive the suffix:

```text
_OpenPartsLibrary
```

The hardware BOM does not include download counts.

## Library Usage

Create a library connection:

```python
from openpartslibrary.db import PartsLibrary

pl = PartsLibrary()
```

Import components and suppliers from a spreadsheet:

```python
from pathlib import Path

spreadsheet_path = Path("openpartslibrary") / "sample" / "components.ods"
pl.import_from_spreadsheet(
    spreadsheet_path,
    components_cad_dir_path=Path("openpartslibrary") / "sample" / "components-cad",
)
```

Query components:

```python
from openpartslibrary.models import Component

components = pl.session.query(Component).all()
```

## Project Structure

```text
app.py                         Flask web entrypoint
run_desktop.py                 PyWebView desktop wrapper
openpartslibrary/
  __init__.py                  App bootstrap
  admin.py                     Flask-Admin setup
  db.py                        SQLAlchemy session and spreadsheet import
  desktop.py                   Desktop file-opening helper
  downloads.py                 Download filename and event helpers
  hbom.py                      SPDX hardware BOM generation
  models.py                    SQLAlchemy models
  paths.py                     Runtime path setup
  routes.py                    Public Flask routes
  startup.py                   Startup migration and sample bootstrap
  sample/                      Sample spreadsheet and CAD data
  static/                      Frontend assets and vendor libraries
  templates/                   Public app templates
```

## Notes

Generated build output, runtime databases, runtime CAD copies, and generated exports are intentionally excluded from the source tree. Keep third-party frontend libraries under `openpartslibrary/static/` unchanged unless intentionally upgrading them.
