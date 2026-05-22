"""Import and export OpenPartsLibrary parts package zip files."""

import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

import pandas as pd

from openpartslibrary.models import Component, Supplier


@dataclass(frozen=True)
class PartsPackageImportResult:
    """Summary of a parts package import."""

    imported_parts_count: int = 0
    skipped_existing_uuid_count: int = 0


class PartsPackage:
    """Parts package importer/exporter for spreadsheet plus CAD zip files."""

    SPREADSHEET_NAMES = ("parts.ods", "parts.xlsx", "components.ods", "components.xlsx")
    CAD_DIR_NAMES = ("parts-cad", "components-cad")

    def __init__(self, parts_library):
        """Bind the package interface to a :class:`PartsLibrary` instance."""

        self.parts_library = parts_library

    def import_zip(self, zip_file_path):
        """Import a package zip containing a spreadsheet and CAD directory."""

        zip_path = Path(zip_file_path).expanduser().resolve()
        with tempfile.TemporaryDirectory(prefix="opl-parts-package-") as temp_dir:
            extract_dir = Path(temp_dir)
            with zipfile.ZipFile(zip_path) as package_zip:
                self._safe_extract(package_zip, extract_dir)

            spreadsheet_path = self._find_first_existing(extract_dir, self.SPREADSHEET_NAMES)
            cad_dir_path = self._find_first_existing(extract_dir, self.CAD_DIR_NAMES)
            if spreadsheet_path is None:
                raise ValueError("Parts package must contain parts.ods, parts.xlsx, components.ods, or components.xlsx.")
            if cad_dir_path is None or not cad_dir_path.is_dir():
                raise ValueError("Parts package must contain a parts-cad or components-cad folder.")

            filtered_spreadsheet_path, skipped_existing_uuid_count, import_candidate_uuids = self._filter_existing_component_uuids(
                spreadsheet_path,
                extract_dir,
            )
            self.parts_library.import_from_spreadsheet(
                filtered_spreadsheet_path,
                components_cad_dir_path=cad_dir_path,
            )
            imported_parts_count = self._count_imported_component_uuids(import_candidate_uuids)
            return PartsPackageImportResult(
                imported_parts_count=imported_parts_count,
                skipped_existing_uuid_count=skipped_existing_uuid_count,
            )

    def export_zip(self, output_zip_path=None, spreadsheet_name="parts.ods"):
        """Export current parts to a package zip and return its path."""

        if output_zip_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_zip_path = self.parts_library.data_dir_path / f"parts_{timestamp}_OPL.zip"

        output_path = Path(output_zip_path).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="opl-parts-export-") as temp_dir:
            export_dir = Path(temp_dir)
            cad_dir_path = export_dir / "parts-cad"
            cad_dir_path.mkdir(parents=True, exist_ok=True)

            spreadsheet_path = export_dir / spreadsheet_name
            self._write_spreadsheet(spreadsheet_path, cad_dir_path)

            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as package_zip:
                package_zip.write(spreadsheet_path, spreadsheet_path.name)
                for cad_path in sorted(cad_dir_path.rglob("*")):
                    if cad_path.is_file():
                        package_zip.write(cad_path, PurePosixPath("parts-cad", cad_path.name).as_posix())

        return output_path

    def _write_spreadsheet(self, spreadsheet_path, cad_dir_path):
        """Write component and supplier sheets for the package."""

        components = (
            self.parts_library.session.query(Component)
            .order_by(Component.number.asc(), Component.name.asc())
            .all()
        )
        suppliers = (
            self.parts_library.session.query(Supplier)
            .order_by(Supplier.name.asc())
            .all()
        )

        component_rows = []
        used_cad_names = set()
        for component in components:
            cad_file_name = component.cad_file.name if component.cad_file else None
            if cad_file_name:
                cad_file_name = self._copy_cad_file(component, cad_dir_path, used_cad_names) or cad_file_name

            component_rows.append({
                "uuid": component.uuid,
                "number": component.number,
                "name": component.name,
                "description": component.description,
                "revision": component.revision,
                "lifecycle_state": component.lifecycle_state,
                "owner": component.owner,
                "material": component.material,
                "unit_price": component.unit_price,
                "currency": component.currency,
                "supplier_uuid": component.supplier.uuid if component.supplier else None,
                "supplier_name": component.supplier.name if component.supplier else None,
                "cad_file_name": cad_file_name,
                "cad_file_link": f"parts-cad/{cad_file_name}" if cad_file_name else None,
            })

        supplier_rows = [
            {
                "uuid": supplier.uuid,
                "name": supplier.name,
                "description": supplier.description,
                "street": supplier.street,
                "street_number": supplier.house_number,
                "postal_code": supplier.postal_code,
                "city": supplier.city,
                "country": supplier.country,
            }
            for supplier in suppliers
        ]

        writer_kwargs = {"engine": "odf"} if spreadsheet_path.suffix.lower() == ".ods" else {}
        with pd.ExcelWriter(spreadsheet_path, **writer_kwargs) as writer:
            pd.DataFrame(component_rows).to_excel(writer, sheet_name="components", index=False)
            pd.DataFrame(supplier_rows).to_excel(writer, sheet_name="suppliers", index=False)

    def _filter_existing_component_uuids(self, spreadsheet_path, working_dir):
        """Create an import spreadsheet without components already in the DB."""

        components_df = self.parts_library._read_spreadsheet(
            spreadsheet_path,
            "components",
            dtype={"number": str},
        )
        suppliers_df = self.parts_library._read_spreadsheet(spreadsheet_path, "suppliers")

        existing_uuids = {
            uuid_value
            for (uuid_value,) in self.parts_library.session.query(Component.uuid).all()
        }

        valid_mask = (
            components_df["uuid"].notna()
            & components_df["number"].notna()
            & components_df["name"].notna()
            & components_df["uuid"].astype(str).map(self.parts_library._is_valid_part_uuid)
        )
        valid_components_df = components_df.loc[valid_mask].copy()
        skipped_mask = valid_components_df["uuid"].astype(str).isin(existing_uuids)
        skipped_count = len(set(valid_components_df.loc[skipped_mask, "uuid"].astype(str)))
        filtered_components_df = valid_components_df.loc[~skipped_mask].copy()
        import_candidate_uuids = set(filtered_components_df["uuid"].astype(str))

        filtered_spreadsheet_path = Path(working_dir) / f"filtered-{Path(spreadsheet_path).name}"
        writer_kwargs = {"engine": "odf"} if filtered_spreadsheet_path.suffix.lower() == ".ods" else {}
        with pd.ExcelWriter(filtered_spreadsheet_path, **writer_kwargs) as writer:
            filtered_components_df.to_excel(writer, sheet_name="components", index=False)
            suppliers_df.to_excel(writer, sheet_name="suppliers", index=False)

        return filtered_spreadsheet_path, skipped_count, import_candidate_uuids

    def _count_imported_component_uuids(self, component_uuids):
        """Count candidate component UUIDs that exist after import."""

        if not component_uuids:
            return 0
        return (
            self.parts_library.session.query(Component)
            .filter(Component.uuid.in_(component_uuids))
            .count()
        )

    def _copy_cad_file(self, component, cad_dir_path, used_cad_names):
        """Copy a component CAD file using the original package filename."""

        cad_file = component.cad_file
        source_candidates = self.parts_library.stored_cad_path_candidates(component)
        source_path = next((candidate for candidate in source_candidates if candidate and candidate.exists()), None)
        if source_path is None:
            return None

        destination_name = self._unique_filename(
            self.parts_library._stored_cad_filename(component, source_path.suffix),
            used_cad_names,
        )
        shutil.copy2(source_path, cad_dir_path / destination_name)
        return destination_name

    def _unique_filename(self, filename, used_filenames):
        """Return a filename that is unique within the package."""

        path = Path(filename)
        candidate = path.name
        index = 2
        while candidate.lower() in used_filenames:
            candidate = f"{path.stem}-{index}{path.suffix}"
            index += 1
        used_filenames.add(candidate.lower())
        return candidate

    def _find_first_existing(self, root_path, relative_paths):
        """Return the first existing path from a set of package-relative names."""

        for relative_path in relative_paths:
            candidate = root_path / relative_path
            if candidate.exists():
                return candidate
        return None

    def _safe_extract(self, package_zip, destination_path):
        """Extract a zip without allowing path traversal."""

        destination_path = destination_path.resolve()
        for member in package_zip.infolist():
            member_path = destination_path / member.filename
            if not member_path.resolve().is_relative_to(destination_path):
                raise ValueError("Parts package contains an unsafe path.")
        package_zip.extractall(destination_path)
