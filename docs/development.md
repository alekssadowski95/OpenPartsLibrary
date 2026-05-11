# Development Guide

## Local Loop

Use the Flask server during normal development:

```console
python app.py
```

The app creates the runtime SQLite database and file directories automatically.
Delete `instance/data/` only when you intentionally want to rebuild local sample
data from the bundled spreadsheet.

## Adding Features

Prefer adding logic to the module that already owns the behavior:

- Search changes belong in `search.py`.
- BOM tree behavior belongs in `boms.py` or `session_boms.py`.
- Public page and download behavior belongs in `routes.py`.
- Admin-only workflows belong in `admin.py`.
- Database schema changes belong in `models.py` and may need migration support in `startup.py`.

Keep route functions thin when possible.  Shared behavior that is needed by more
than one route should become a helper near the routes or a domain helper in the
appropriate module.

## Documentation

Public modules, classes, and functions use Sphinx-compatible docstrings.  New
developer-facing documentation should be added as Markdown files in `docs/` and
linked from `docs/index.rst`.
