# Installation

## Requirements

- Python 3.10 or newer
- The packages listed in `requirements.txt`
- Optional FreeCAD and Blender command templates for generated CAD thumbnails

## Web App

Install dependencies:

```console
pip install -r requirements.txt
```

Run the development server:

```console
python app.py
```

Open `http://localhost:5000`.

## Desktop App

Run the desktop wrapper:

```console
python run_desktop.py
```

Build the Windows desktop ZIP:

```console
powershell -ExecutionPolicy Bypass -File scripts/build_windows_desktop.ps1
```

Runtime data is stored in `instance/data/` for the web app.  The packaged
desktop build stores data beside the executable.

## Documentation

Build this site with:

```console
python -m sphinx -b html docs docs/_build/html
```

The generated HTML entry point is `docs/_build/html/index.html`.
