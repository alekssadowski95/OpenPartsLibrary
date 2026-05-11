"""Database setup and spreadsheet import services."""

import shutil
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from openpartslibrary.models import Base, Component, File, Supplier


class PartsLibrary:
    """Facade around the local SQLite database and imported library files.

    :param db_path: Optional explicit SQLite database path.
    :param data_dir_path: Optional runtime data directory for copied files.
    """

    def __init__(self, db_path=None, data_dir_path=None):
        """Initialize paths, create database tables, and open a session."""

        package_dir = Path(__file__).resolve().parent
        self.data_dir_path = Path(data_dir_path or package_dir / "data").expanduser().resolve()
        self.data_cad_dir_path = self.data_dir_path / "cad"
        self.data_files_dir_path = self.data_dir_path / "files"
        self.sample_data_dir_path = package_dir / "sample"

        self.data_cad_dir_path.mkdir(parents=True, exist_ok=True)
        self.data_files_dir_path.mkdir(parents=True, exist_ok=True)

        self.db_path = Path(db_path or self.data_dir_path / "parts.db").expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(f"sqlite:///{self.db_path.as_posix()}")
        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)
        self.session = self.session_factory()

    def get_default_sample_spreadsheet_path(self):
        """Return the bundled sample spreadsheet path.

        :raises FileNotFoundError: If no supported sample spreadsheet exists.
        :return: Path to ``components.ods`` or ``components.xlsx``.
        """

        for candidate in ("components.ods", "components.xlsx"):
            candidate_path = self.sample_data_dir_path / candidate
            if candidate_path.exists():
                return candidate_path
        raise FileNotFoundError(f"No supported sample spreadsheet found in {self.sample_data_dir_path}")

    def import_from_spreadsheet(
        self,
        spreadsheet_file_path,
        components_sheet_name="components",
        components_cad_dir_path=None,
        suppliers_sheet_name="suppliers",
    ):
        """Import components, suppliers, and optional CAD files from a sheet.

        :param spreadsheet_file_path: Spreadsheet with component/supplier tabs.
        :param components_sheet_name: Sheet containing component rows.
        :param components_cad_dir_path: Optional directory containing CAD files.
        :param suppliers_sheet_name: Sheet containing supplier rows.
        :return: ``None``.
        """

        components_df = self._read_spreadsheet(spreadsheet_file_path, components_sheet_name, dtype={"number": str})
        suppliers_df = self._read_spreadsheet(spreadsheet_file_path, suppliers_sheet_name)
        suppliers_by_uuid = self._import_suppliers(suppliers_df)

        for _, row in components_df.iterrows():
            if pd.isna(row.get("uuid")) or pd.isna(row.get("number")) or pd.isna(row.get("name")):
                continue

            component = self.session.query(Component).filter_by(uuid=str(row["uuid"])).first()
            if component is None:
                component = Component(uuid=str(row["uuid"]))
                self.session.add(component)

            component.number = str(row["number"])
            component.name = str(row["name"])
            component.description = self._clean_value(row.get("description"))
            component.revision = self._clean_value(row.get("revision"))
            component.lifecycle_state = self._clean_value(row.get("lifecycle_state"))
            component.owner = self._clean_value(row.get("owner"))
            component.material = self._clean_value(row.get("material"))
            component.unit_price = self._clean_value(row.get("unit_price"))
            component.currency = self._clean_value(row.get("currency"))
            component.date_modified = datetime.utcnow()

            supplier_uuid = self._clean_value(row.get("supplier_uuid"))
            if supplier_uuid:
                component.supplier = suppliers_by_uuid.get(supplier_uuid)

            self._attach_cad_file_from_row(component, row, spreadsheet_file_path, components_cad_dir_path)

        self.session.commit()

    def sync_cad_files_from_spreadsheet(self, spreadsheet_file_path, components_sheet_name="components"):
        """Copy CAD files referenced by an existing component spreadsheet."""

        spreadsheet_path = Path(spreadsheet_file_path).expanduser().resolve()
        components_df = self._read_spreadsheet(spreadsheet_path, components_sheet_name, dtype={"number": str})

        for _, row in components_df.iterrows():
            component_uuid = self._clean_value(row.get("uuid"))
            cad_file_name = self._clean_value(row.get("cad_file_name"))
            if not component_uuid or not cad_file_name:
                continue

            component = self.session.query(Component).filter_by(uuid=component_uuid).first()
            if component is None:
                continue

            cad_file = component.cad_file
            if cad_file is None:
                cad_file = File(uuid=str(uuid.uuid4()), name=cad_file_name, description="This is a CAD file.")
                component.cad_file = cad_file
                self.session.add(cad_file)

            source_path = self._find_cad_source(spreadsheet_path, cad_file_name, row.get("cad_file_link"))
            if source_path is None:
                continue

            destination_path = self.data_cad_dir_path / f"{cad_file.uuid}{source_path.suffix}"
            if not destination_path.exists():
                shutil.copy2(source_path, destination_path)

        self.session.commit()

    def sync_suppliers_from_spreadsheet(
        self,
        spreadsheet_file_path,
        components_sheet_name="components",
        suppliers_sheet_name="suppliers",
    ):
        """Refresh supplier records and component supplier links from a sheet."""

        components_df = self._read_spreadsheet(spreadsheet_file_path, components_sheet_name, dtype={"number": str})
        suppliers_df = self._read_spreadsheet(spreadsheet_file_path, suppliers_sheet_name)
        suppliers_by_uuid = self._import_suppliers(suppliers_df)
        suppliers_by_name = {
            supplier.name.strip().lower(): supplier
            for supplier in suppliers_by_uuid.values()
            if supplier.name
        }

        for _, row in components_df.iterrows():
            component_uuid = self._clean_value(row.get("uuid"))
            if not component_uuid:
                continue

            component = self.session.query(Component).filter_by(uuid=component_uuid).first()
            if component is None:
                continue

            supplier_uuid = self._clean_value(row.get("supplier_uuid"))
            supplier_name = self._clean_value(row.get("supplier_name"))
            supplier = suppliers_by_uuid.get(supplier_uuid)
            if supplier is None and supplier_name:
                supplier = suppliers_by_name.get(str(supplier_name).strip().lower())

            if supplier is not None:
                component.supplier = supplier

        self.session.commit()

    def _import_suppliers(self, suppliers_df):
        """Upsert supplier rows from a pandas DataFrame.

        :return: Mapping of supplier UUID to :class:`Supplier`.
        :rtype: dict
        """

        suppliers_by_uuid = {}

        for _, row in suppliers_df.iterrows():
            supplier_uuid = self._clean_value(row.get("uuid"))
            if not supplier_uuid:
                continue

            supplier = self.session.query(Supplier).filter_by(uuid=supplier_uuid).first()
            if supplier is None:
                supplier = Supplier(uuid=supplier_uuid)
                self.session.add(supplier)

            supplier.name = self._clean_value(row.get("name")) or "Unknown supplier"
            supplier.description = self._clean_value(row.get("description"))
            supplier.street = self._clean_value(row.get("street"))
            supplier.house_number = self._clean_value(row.get("street_number"))
            supplier.postal_code = self._clean_value(row.get("postal_code"))
            supplier.city = self._clean_value(row.get("city"))
            supplier.country = self._clean_value(row.get("country"))
            suppliers_by_uuid[supplier_uuid] = supplier

        self.session.flush()
        return suppliers_by_uuid

    def _attach_cad_file_from_row(self, component, row, spreadsheet_file_path, components_cad_dir_path=None):
        """Attach or update a component CAD-file record from a spreadsheet row."""

        cad_file_name = self._clean_value(row.get("cad_file_name"))
        if not cad_file_name:
            return

        if component.cad_file is None:
            component.cad_file = File(uuid=str(uuid.uuid4()), name=cad_file_name, description="This is a CAD file.")
        else:
            component.cad_file.name = cad_file_name

        if components_cad_dir_path is None:
            return

        source_path = self._find_cad_source(Path(spreadsheet_file_path), cad_file_name, row.get("cad_file_link"), components_cad_dir_path)
        if source_path is None:
            return

        destination_path = self.data_cad_dir_path / f"{component.cad_file.uuid}{source_path.suffix}"
        if not destination_path.exists():
            shutil.copy2(source_path, destination_path)

    def _find_cad_source(self, spreadsheet_path, cad_file_name, cad_link=None, components_cad_dir_path=None):
        """Find a CAD source file near the spreadsheet or in the sample CAD dir."""

        spreadsheet_path = Path(spreadsheet_path).expanduser().resolve()
        search_dir = Path(components_cad_dir_path) if components_cad_dir_path else self.sample_data_dir_path / "components-cad"
        candidates = [search_dir / candidate for candidate in self._cad_filename_candidates(cad_file_name)]

        clean_cad_link = self._clean_value(cad_link)
        if clean_cad_link:
            candidates.extend(spreadsheet_path.parent / candidate for candidate in self._cad_filename_candidates(clean_cad_link))

        return next((candidate for candidate in candidates if candidate.exists()), None)

    def _cad_filename_candidates(self, cad_file_name):
        """Return tolerated filename variants for imported CAD references."""

        cad_file_name = str(cad_file_name)
        return dict.fromkeys([
            cad_file_name,
            cad_file_name.replace("_", "", 1),
            cad_file_name.replace("_", ""),
        ])

    def _read_spreadsheet(self, spreadsheet_file_path, sheet_name, dtype=None):
        """Read a spreadsheet sheet into a pandas DataFrame."""

        spreadsheet_path = Path(spreadsheet_file_path).expanduser().resolve()
        engine = "odf" if spreadsheet_path.suffix.lower() == ".ods" else None
        return pd.read_excel(spreadsheet_path, sheet_name=sheet_name, dtype=dtype, engine=engine)

    def _clean_value(self, value):
        """Normalize empty spreadsheet values to ``None`` and trim text."""

        if pd.isna(value):
            return None
        if isinstance(value, float) and value.is_integer():
            return str(int(value))
        if isinstance(value, str):
            cleaned_value = value.strip()
            return cleaned_value or None
        return value
