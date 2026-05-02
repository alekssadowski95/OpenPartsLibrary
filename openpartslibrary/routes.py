import io
import json
import zipfile
from urllib.parse import urlencode

from flask import jsonify, redirect, render_template, request, send_file, send_from_directory, url_for
from sqlalchemy import asc, desc, or_

from openpartslibrary.desktop import open_with_default_application
from openpartslibrary.downloads import record_download_event, with_openpartslibrary_suffix
from openpartslibrary.hbom import build_spdx_hardware_bom
from openpartslibrary.models import Component, File, Supplier


def build_components_url(overrides=None):
    query_args = request.args.to_dict(flat=True)
    for key, value in (overrides or {}).items():
        if value is None or value == "":
            query_args.pop(key, None)
        else:
            query_args[key] = value

    query_string = urlencode(query_args)
    if not query_string:
        return url_for("components")
    return f"{url_for('components')}?{query_string}"


def register_routes(app, parts_library):
    session = parts_library.session
    cad_dir = app.config["CAD_DIR"]
    file_dir = app.config["FILE_DIR"]

    @app.route("/")
    def home():
        return redirect(url_for("components"))

    @app.route("/components", defaults={"search_query": None})
    def components(search_query):
        search_query = request.args.get("search_query", "")
        supplier_filter = request.args.get("supplier", "")
        material_filter = request.args.get("material", "")
        currency_filter = request.args.get("currency", "")
        price_min = request.args.get("price_min", "")
        price_max = request.args.get("price_max", "")
        sort_key = request.args.get("sort", "name")
        direction = request.args.get("direction", "asc")
        like_pattern = f"%{search_query}%"

        query = session.query(Component).outerjoin(Component.supplier)

        if search_query:
            query = query.filter(or_(
                Component.name.ilike(like_pattern),
                Component.description.ilike(like_pattern),
                Component.number.ilike(like_pattern),
            ))

        if supplier_filter and supplier_filter.isdigit():
            query = query.filter(Component.supplier_id == int(supplier_filter))

        if material_filter:
            query = query.filter(Component.material == material_filter)

        if currency_filter:
            query = query.filter(Component.currency == currency_filter)

        if price_min:
            try:
                query = query.filter(Component.unit_price >= float(price_min))
            except ValueError:
                price_min = ""

        if price_max:
            try:
                query = query.filter(Component.unit_price <= float(price_max))
            except ValueError:
                price_max = ""

        sort_columns = {
            "name": Component.name,
            "number": Component.number,
            "supplier": Supplier.name,
            "unit_price": Component.unit_price,
            "description": Component.description,
        }
        sort_column = sort_columns.get(sort_key, Component.name)
        sort_direction = desc if direction == "desc" else asc
        component_results = query.order_by(sort_direction(sort_column)).limit(1000).all()

        suppliers = session.query(Supplier).order_by(Supplier.name).all()
        materials = [
            value[0]
            for value in session.query(Component.material)
            .filter(Component.material.isnot(None), Component.material != "")
            .distinct()
            .order_by(Component.material)
            .all()
        ]
        currencies = [
            value[0]
            for value in session.query(Component.currency)
            .filter(Component.currency.isnot(None), Component.currency != "")
            .distinct()
            .order_by(Component.currency)
            .all()
        ]

        component_cad_filenames = {}
        for component in component_results:
            if component.cad_file is None:
                continue
            cad_filename = f"{component.cad_file.uuid}.FCStd"
            if (cad_dir / cad_filename).exists():
                component_cad_filenames[component.uuid] = cad_filename

        return render_template(
            "components.html",
            components=component_results,
            len=len,
            search_query=search_query,
            component_cad_filenames=component_cad_filenames,
            suppliers=suppliers,
            materials=materials,
            currencies=currencies,
            filters={
                "supplier": supplier_filter,
                "material": material_filter,
                "currency": currency_filter,
                "price_min": price_min,
                "price_max": price_max,
            },
            sort_key=sort_key,
            direction=direction,
            components_url=build_components_url,
        )

    @app.route("/component_view/<uuid>")
    def component_view(uuid):
        component = session.query(Component).filter_by(uuid=uuid).first()
        if component is None:
            return f"Component not found with UUID: {uuid}", 404

        component_cad_filepath = None
        component_cad_filename = None
        if component.cad_file is not None:
            cad_path = cad_dir / f"{component.cad_file.uuid}.FCStd"
            if cad_path.exists():
                component_cad_filepath = str(cad_path.resolve())
                component_cad_filename = cad_path.name

        return render_template(
            "component.html",
            component=component,
            len=len,
            component_cad_filepath=component_cad_filepath,
            component_cad_filename=component_cad_filename,
            files=component.files,
            used_in_files=[],
        )

    @app.route("/component/<uuid>/download-cad")
    def component_download_cad(uuid):
        component = session.query(Component).filter_by(uuid=uuid).first()
        if component is None or component.cad_file is None:
            return "CAD file not found.", 404

        cad_filename = f"{component.cad_file.uuid}.FCStd"
        cad_path = cad_dir / cad_filename
        if not cad_path.exists():
            return "CAD file not found.", 404

        part_number = str(component.number or component.uuid).replace("/", "-").replace("\\", "-")
        original_name = component.cad_file.name or cad_filename
        downloaded_filename = with_openpartslibrary_suffix(f"{part_number}_{original_name}")
        record_download_event(
            session,
            "component_cad",
            downloaded_filename,
            component=component,
            file=component.cad_file,
            quantity=1,
        )

        return send_file(cad_path, as_attachment=True, download_name=downloaded_filename)

    @app.route("/selection/download", methods=["POST"])
    def selection_download():
        selection_items = request.get_json(silent=True) or []
        if not isinstance(selection_items, list):
            return "Expected a list of selected components.", 400

        selected_quantities = {}
        for item in selection_items:
            if isinstance(item, dict):
                component_uuid = str(item.get("uuid", ""))
                quantity = int(item.get("quantity") or 1)
            else:
                component_uuid = str(item)
                quantity = 1

            if component_uuid:
                selected_quantities[component_uuid] = selected_quantities.get(component_uuid, 0) + quantity

        zip_buffer = io.BytesIO()
        files_added = 0
        bom_components = []

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for component_uuid, quantity in selected_quantities.items():
                component = session.query(Component).filter_by(uuid=component_uuid).first()
                if component is None:
                    continue

                part_number = str(component.number or component.uuid).replace("/", "-").replace("\\", "-")
                archive_name = None

                if component.cad_file is not None:
                    cad_filename = f"{component.cad_file.uuid}.FCStd"
                    cad_path = cad_dir / cad_filename
                    if cad_path.exists():
                        original_name = component.cad_file.name or cad_filename
                        archive_name = with_openpartslibrary_suffix(f"{part_number}_{original_name}")
                        zip_file.write(cad_path, archive_name)
                        files_added += 1
                        record_download_event(
                            session,
                            "selection_cad_item",
                            archive_name,
                            component=component,
                            file=component.cad_file,
                            quantity=quantity,
                        )

                bom_components.append({
                    "uuid": component.uuid,
                    "name": component.name,
                    "part_number": component.number,
                    "quantity": quantity,
                    "price_per_item": str(component.unit_price or ""),
                    "currency": component.currency or "",
                    "cad_file": archive_name,
                    "description": component.description or "",
                    "supplier": component.supplier.name if component.supplier else "",
                })

            if bom_components:
                zip_file.writestr(
                    with_openpartslibrary_suffix("hardware-bom.spdx.jsonld"),
                    json.dumps(build_spdx_hardware_bom(bom_components), indent=2),
                )

        if files_added == 0 and not bom_components:
            return "No CAD files found for the current selection.", 404

        zip_buffer.seek(0)
        zip_download_name = with_openpartslibrary_suffix("openpartslibrary-selection.zip")
        record_download_event(session, "selection_zip", zip_download_name, quantity=sum(selected_quantities.values()))
        return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=zip_download_name)

    @app.route("/selection/components", methods=["POST"])
    def selection_components():
        selection_items = request.get_json(silent=True) or []
        if not isinstance(selection_items, list):
            return jsonify([])

        components = []
        quantities_by_uuid = {}
        for item in selection_items:
            if isinstance(item, dict):
                component_uuid = str(item.get("uuid", ""))
                quantity = item.get("quantity", 1)
            else:
                component_uuid = str(item)
                quantity = 1

            if component_uuid:
                quantities_by_uuid[component_uuid] = quantities_by_uuid.get(component_uuid, 0) + int(quantity or 1)

        for component_uuid, quantity in quantities_by_uuid.items():
            component = session.query(Component).filter_by(uuid=component_uuid).first()
            if component is None:
                continue

            components.append({
                "uuid": component.uuid,
                "name": component.name,
                "part_number": component.number,
                "quantity": quantity,
                "price_per_item": str(component.unit_price or ""),
                "currency": component.currency or "",
            })

        return jsonify(components)

    @app.route("/file/download/<file_uuid>")
    def download_file(file_uuid):
        file = session.query(File).filter_by(uuid=file_uuid).first()
        if file is None:
            return f"File not found with UUID: {file_uuid}", 404

        matching_files = sorted(file_dir.glob(f"{file.uuid}.*"))
        if not matching_files:
            return "File content not found.", 404

        source_file = matching_files[0]
        downloaded_filename = with_openpartslibrary_suffix(file.name or source_file.name)
        record_download_event(
            session,
            "component_file",
            downloaded_filename,
            file=file,
            quantity=1,
        )
        return send_file(source_file, as_attachment=True, download_name=downloaded_filename)

    @app.route("/viewer/<filename>")
    def viewer(filename):
        if not (cad_dir / filename).exists():
            return "CAD file not found.", 404
        filepath = url_for("serve_model_file", filename=filename)
        return render_template("viewer.html", filepath=filepath)

    @app.route("/static/cad/<filename>")
    def serve_model_file(filename):
        return send_from_directory(str(cad_dir), filename)

    @app.route("/run-freecad-gui/<filepath>")
    def run_freecad_gui(filepath):
        open_with_default_application(filepath)
        return "", 204

    @app.route("/run-libreoffice-gui/<filepath>")
    def run_libreoffice_gui(filepath):
        return "", 204

    @app.route("/run-prepomax-gui/<filepath>")
    def run_prepomax_gui(filepath):
        return "", 204

    @app.route("/run-kicad-gui/<filepath>")
    def run_kicad_gui(filepath):
        return "", 204
