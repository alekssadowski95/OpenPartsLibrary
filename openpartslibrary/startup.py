"""Startup migration and sample-data bootstrap helpers."""

import sqlite3

from openpartslibrary.models import Component


def migrate_legacy_database_schema(db_path):
    """Add columns expected by newer code to an existing SQLite database.

    :param db_path: Path to the runtime SQLite database.
    :return: ``None``.
    """

    if not db_path.exists():
        return

    component_column_definitions = {
        "material": "VARCHAR(200)",
        "supplier_id": "INTEGER",
        "manufacturer_number": "VARCHAR(100)",
    }

    with sqlite3.connect(str(db_path)) as connection:
        cursor = connection.cursor()
        cursor.execute("PRAGMA table_info(components)")
        component_columns = {row[1] for row in cursor.fetchall()}

        for column_name, column_type in component_column_definitions.items():
            if column_name in component_columns:
                continue
            cursor.execute(
                f"ALTER TABLE components ADD COLUMN {column_name} {column_type}"
            )

        connection.commit()


def bootstrap_sample_data(parts_library):
    """Populate or refresh the database from the bundled sample spreadsheet.

    :param parts_library: Initialized :class:`openpartslibrary.db.PartsLibrary`.
    :return: ``None``.
    """

    sample_spreadsheet_path = parts_library.get_default_sample_spreadsheet_path()

    if not parts_library.session.query(Component).first():
        parts_library.import_from_spreadsheet(
            sample_spreadsheet_path,
            components_cad_dir_path=parts_library.sample_data_dir_path / "components-cad",
        )
    else:
        parts_library.sync_suppliers_from_spreadsheet(sample_spreadsheet_path)

    parts_library.sync_cad_files_from_spreadsheet(sample_spreadsheet_path)
