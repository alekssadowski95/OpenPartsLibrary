"""Public Flask routes and route-adjacent view helpers.

This module keeps HTTP concerns together: query parsing, template rendering,
download responses, thumbnail responses, and user-session BOM actions.
"""

import io
import json
import zipfile
from datetime import datetime
from urllib.parse import urlencode

from flask import jsonify, redirect, render_template, request, send_file, send_from_directory, url_for
from sqlalchemy import asc, desc, func

from openpartslibrary.boms import bom_part_quantities, ensure_part_boms, format_bom_cost, get_bom_options, get_created_boms
from openpartslibrary.admin import node_editor_payload_from_request
from openpartslibrary.downloads import branded_library_filename, branded_part_filename, record_download_event
from openpartslibrary.hbom import build_spdx_hardware_bom
from openpartslibrary.i18n import gettext as _
from openpartslibrary.models import BillOfMaterials, Component, DownloadEvent, File, Supplier
from openpartslibrary.search import normalize_search_text, partial_fuzzy_ratio, search_parts, token_overlap_score
from openpartslibrary.session_boms import get_session_bom, get_session_bom_record, get_session_boms, save_session_bom_record, update_session_bom_record
from openpartslibrary.thumbnails import ensure_cad_thumbnail, placeholder_thumbnail_svg


def selection_quantities_from_payload(selection_items):
    """Aggregate selected component UUIDs into quantities.

    :param selection_items: List of UUID strings or dictionaries with ``uuid``
        and optional ``quantity`` keys.
    :return: Mapping of component UUID to integer quantity.
    :rtype: dict[str, int]
    """

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
    return selected_quantities


def build_parts_url(overrides=None):
    """Build a parts-page URL while preserving active query filters.

    :param overrides: Query-parameter values to set or remove.
    :return: Relative URL for the parts route.
    :rtype: str
    """

    query_args = request.args.to_dict(flat=True)
    for key, value in (overrides or {}).items():
        if value is None or value == "":
            query_args.pop(key, None)
        else:
            query_args[key] = value

    query_string = urlencode(query_args)
    if not query_string:
        return url_for("parts")
    return f"{url_for('parts')}?{query_string}"


def component_sort_value(component, sort_key):
    """Return a stable sort value for a component and UI sort key.

    :param component: :class:`openpartslibrary.models.Component` instance.
    :param sort_key: Sort field requested by the components page.
    :return: Lowercase text or numeric value suitable for Python sorting.
    """

    if sort_key == "number":
        return str(component.number or "").lower()
    if sort_key == "supplier":
        return str(component.supplier.name if component.supplier else "").lower()
    if sort_key == "unit_price":
        try:
            return float(component.unit_price)
        except (TypeError, ValueError):
            return 0
    if sort_key == "description":
        return str(component.description or "").lower()

    return str(component.name or "").lower()


def component_cad_filename(component, cad_dir):
    """Return the stored CAD filename when the component has a CAD file on disk."""

    if component.cad_file is None:
        return None

    candidate_names = [
        component.cad_file.name,
        f"{component.cad_file.uuid}.FCStd",
    ]
    for cad_filename in candidate_names:
        if cad_filename and (cad_dir / cad_filename).exists():
            return cad_filename
    return None


def component_popularity_counts(db_session, components):
    """Return all-time download counts keyed by component UUID."""

    component_uuids = {component.uuid for component in components}
    if not component_uuids:
        return {}

    return {
        component_uuid: count
        for component_uuid, count in (
            db_session.query(DownloadEvent.component_uuid, func.count(DownloadEvent.id))
            .filter(DownloadEvent.component_uuid.isnot(None))
            .group_by(DownloadEvent.component_uuid)
            .all()
        )
        if component_uuid in component_uuids
    }


def default_component_sort_key(component, cad_filenames, popularity_counts):
    """Sort default component results by CAD availability and popularity."""

    return (
        0 if cad_filenames.get(component.uuid) else 1,
        -popularity_counts.get(component.uuid, 0),
        str(component.name or "").lower(),
        str(component.number or "").lower(),
    )


def bom_has_cad_files(bom, cad_dir):
    """Check whether any part in a BOM has a CAD file on disk.

    :param bom: BOM-like object accepted by :func:`bom_part_quantities`.
    :param cad_dir: Directory containing stored ``.FCStd`` files.
    :return: ``True`` when at least one referenced CAD file exists.
    :rtype: bool
    """

    for row in bom_part_quantities(bom).values():
        component = row["component"]
        if component is not None and component_cad_filename(component, cad_dir):
            return True
    return False


def search_bom_options(db_session, query, limit=60):
    """Search BOM picker options using part search and BOM label matching.

    :param db_session: SQLAlchemy session.
    :param query: User search text.
    :param limit: Maximum options to return.
    :return: Ranked BOM option dictionaries.
    :rtype: list[dict]
    """

    options = get_bom_options(db_session)
    if not str(query or "").strip():
        return options[:limit]

    option_by_id = {option["id"]: option for option in options}
    ranked_ids = []

    part_wrapper_boms = (
        db_session.query(BillOfMaterials)
        .filter(BillOfMaterials.is_part_wrapper.is_(True), BillOfMaterials.component_id.isnot(None))
        .all()
    )
    part_option_id_by_component_id = {
        bom.component_id: bom.id
        for bom in part_wrapper_boms
    }
    components = [bom.component for bom in part_wrapper_boms if bom.component is not None]
    for component in search_parts(query, components, limit=limit):
        option_id = part_option_id_by_component_id.get(component.id)
        if option_id in option_by_id and option_id not in ranked_ids:
            ranked_ids.append(option_id)

    normalized_query = normalize_search_text(query)
    bom_scores = []
    for option in options:
        if option["is_part_wrapper"] or option["id"] in ranked_ids:
            continue
        searchable_text = " ".join([
            option.get("number", ""),
            option.get("name", ""),
            option.get("display_label", ""),
        ])
        score = max(
            partial_fuzzy_ratio(normalized_query, searchable_text),
            token_overlap_score(normalized_query, searchable_text),
        )
        if score >= 58:
            bom_scores.append((score, option))

    bom_scores.sort(key=lambda item: (-item[0], normalize_search_text(item[1].get("display_label", ""))))
    for _, option in bom_scores:
        if option["id"] not in ranked_ids:
            ranked_ids.append(option["id"])
        if len(ranked_ids) >= limit:
            break

    return [option_by_id[option_id] for option_id in ranked_ids[:limit]]


def bom_builder_filter_options(db_session):
    """Return supplier, material, and currency choices for BOM builders.

    :param db_session: SQLAlchemy session.
    :return: Filter option dictionary for JSON and template contexts.
    :rtype: dict
    """

    suppliers = (
        db_session.query(Supplier)
        .filter(
            Supplier.name.isnot(None),
            func.trim(Supplier.name) != "",
            func.lower(func.trim(Supplier.name)) != "unknown supplier",
        )
        .order_by(Supplier.name)
        .all()
    )
    materials = [
        value[0]
        for value in db_session.query(Component.material)
        .filter(Component.material.isnot(None), Component.material != "")
        .distinct()
        .order_by(Component.material)
        .all()
    ]
    currencies = [
        value[0]
        for value in db_session.query(Component.currency)
        .filter(Component.currency.isnot(None), Component.currency != "")
        .distinct()
        .order_by(Component.currency)
        .all()
    ]
    return {
        "suppliers": [{"id": supplier.id, "name": supplier.name} for supplier in suppliers],
        "materials": materials,
        "currencies": currencies,
    }


def bom_builder_library_rows(db_session, query_text="", supplier="", material="", currency="", price_min="", price_max="", limit=50):
    """Return searchable library rows that can be inserted into a BOM.

    :param db_session: SQLAlchemy session.
    :param query_text: Optional free-text search query.
    :param supplier: Optional supplier ID filter.
    :param material: Optional material filter.
    :param currency: Optional currency filter.
    :param price_min: Optional minimum unit price.
    :param price_max: Optional maximum unit price.
    :param limit: Maximum rows to return.
    :return: JSON-serializable library rows.
    :rtype: list[dict]
    """

    options = get_bom_options(db_session)
    part_boms_by_component_id = {
        bom.component_id: bom
        for bom in db_session.query(BillOfMaterials)
        .filter(BillOfMaterials.is_part_wrapper.is_(True), BillOfMaterials.component_id.isnot(None))
        .all()
    }

    query = db_session.query(Component).outerjoin(Component.supplier)

    if supplier and str(supplier).isdigit():
        query = query.filter(Component.supplier_id == int(supplier))
    if material:
        query = query.filter(Component.material == material)
    if currency:
        query = query.filter(Component.currency == currency)
    if price_min:
        try:
            query = query.filter(Component.unit_price >= float(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            query = query.filter(Component.unit_price <= float(price_max))
        except ValueError:
            pass

    filtered_components = query.all()
    component_by_part_option_id = {
        part_boms_by_component_id[component.id].id: component
        for component in filtered_components
        if component.id in part_boms_by_component_id
    }
    filtered_part_option_ids = {
        option_id
        for option_id in component_by_part_option_id
    }
    has_part_filters = any(str(value or "").strip() for value in (supplier, material, currency, price_min, price_max))

    if str(query_text or "").strip():
        ranked_options = search_bom_options(db_session, query_text, limit=max(limit * 4, 120))
    else:
        ranked_options = options

    rows = []
    for option in ranked_options:
        component = None
        if option["is_part_wrapper"]:
            if option["id"] not in filtered_part_option_ids:
                continue
            component = component_by_part_option_id.get(option["id"])
        elif has_part_filters:
            continue

        cost_totals = option.get("cost_totals", {})
        price_label = ""
        if component:
            price_label = " ".join(part for part in (str(component.unit_price or ""), component.currency or "") if part)
        elif cost_totals:
            price_label = ", ".join(f"{amount} {currency}" for currency, amount in sorted(cost_totals.items()))

        rows.append({
            "uuid": component.uuid if component else "",
            "name": component.name if component else option["name"],
            "number": option.get("number", ""),
            "description": component.description or "" if component else "",
            "supplier": component.supplier.name if component and component.supplier else "",
            "material": component.material or "" if component else "",
            "unit_price": str(component.unit_price or "") if component else "",
            "currency": component.currency or "" if component else "",
            "price_label": price_label,
            "option_id": option["id"],
            "part_bom_id": option["id"],
            "display_label": option["display_label"],
            "is_part_wrapper": option["is_part_wrapper"],
            "entry_type": "part" if option["is_part_wrapper"] else "bom",
            "cost_totals": cost_totals,
        })
        if len(rows) >= limit:
            break
    return rows


def bom_builder_part_rows(db_session, query_text="", supplier="", material="", currency="", price_min="", price_max="", limit=50):
    """Return searchable part rows that can be inserted into a BOM."""

    rows = bom_builder_library_rows(
        db_session,
        query_text=query_text,
        supplier=supplier,
        material=material,
        currency=currency,
        price_min=price_min,
        price_max=price_max,
        limit=limit,
    )
    return [row for row in rows if row["is_part_wrapper"]]


def register_routes(app, parts_library):
    """Register all public routes on a Flask application.

    :param app: Flask application instance.
    :param parts_library: Initialized :class:`openpartslibrary.db.PartsLibrary`.
    :return: ``None``.
    """

    session = parts_library.session
    cad_dir = app.config["CAD_DIR"]
    file_dir = app.config["FILE_DIR"]
    mesh_dir = app.config["MESH_DIR"]
    thumbnail_dir = app.config["THUMBNAIL_DIR"]

    @app.route("/")
    def home():
        return redirect(url_for("parts"))

    @app.route("/components", defaults={"search_query": None})
    def legacy_components_redirect(search_query):
        return redirect(build_parts_url(), code=301)

    @app.route("/parts", defaults={"search_query": None})
    def parts(search_query):
        search_query = request.args.get("search_query", "").strip()
        supplier_filter = request.args.get("supplier", "")
        material_filter = request.args.get("material", "")
        currency_filter = request.args.get("currency", "")
        price_min = request.args.get("price_min", "")
        price_max = request.args.get("price_max", "")
        sort_key = request.args.get("sort", "")
        direction = request.args.get("direction", "asc")
        explicit_sort = sort_key in {"name", "number", "supplier", "unit_price", "description"}

        query = session.query(Component).outerjoin(Component.supplier)

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

        if search_query:
            matching_components = search_parts(search_query, query.all(), limit=1000)
            if explicit_sort:
                reverse_sort = direction == "desc"
                component_results = sorted(
                    matching_components,
                    key=lambda component: component_sort_value(component, sort_key),
                    reverse=reverse_sort,
                )
            else:
                component_results = matching_components
        else:
            if explicit_sort:
                component_results = query.order_by(sort_direction(sort_column)).limit(1000).all()
            else:
                component_results = query.all()

        suppliers = (
            session.query(Supplier)
            .filter(
                Supplier.name.isnot(None),
                func.trim(Supplier.name) != "",
                func.lower(func.trim(Supplier.name)) != "unknown supplier",
            )
            .order_by(Supplier.name)
            .all()
        )
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
            cad_filename = component_cad_filename(component, cad_dir)
            if cad_filename:
                component_cad_filenames[component.uuid] = cad_filename

        if not search_query and not explicit_sort:
            popularity_counts = component_popularity_counts(session, component_results)
            component_results = sorted(
                component_results,
                key=lambda component: default_component_sort_key(component, component_cad_filenames, popularity_counts),
            )[:1000]

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
            parts_url=build_parts_url,
        )

    @app.route("/boms")
    def boms():
        ensure_part_boms(session)
        user_boms = get_session_boms(session)
        admin_boms = get_created_boms(session)
        return render_template(
            "boms.html",
            boms=admin_boms,
            user_boms=user_boms,
            total_bom_count=len(user_boms) + len(admin_boms),
            search_query=request.args.get("search_query", ""),
            format_bom_cost=format_bom_cost,
            bom_has_cad_files=lambda bom: bom_has_cad_files(bom, cad_dir),
        )

    @app.route("/bom-options/search")
    def bom_options_search():
        ensure_part_boms(session)
        return jsonify(search_bom_options(session, request.args.get("q", ""), limit=60))

    @app.route("/bom-builder/parts-library")
    def bom_builder_parts_library():
        ensure_part_boms(session)
        return jsonify({
            "parts": bom_builder_library_rows(
                session,
                request.args.get("search_query", ""),
                request.args.get("supplier", ""),
                request.args.get("material", ""),
                request.args.get("currency", ""),
                request.args.get("price_min", ""),
                request.args.get("price_max", ""),
            )
        })

    @app.route("/bom-builder", methods=["GET", "POST"])
    def public_bom_node_editor():
        ensure_part_boms(session)
        if request.method == "POST":
            if request.form.get("name", "").strip():
                save_session_bom_record(
                    request.form.get("name"),
                    request.form.get("description", ""),
                    node_editor_payload_from_request(),
                )
            return redirect(url_for("boms"))

        return render_template(
            "admin/bom_node_editor.html",
            bom_options=get_bom_options(session),
            edit_bom=None,
            form_action=url_for("public_bom_node_editor"),
            table_editor_url=url_for("boms"),
            draft_storage_key="openpartslibrary:public-bom-node-editor:new",
            initial_items=[],
            loadable_boms=[],
            show_load_bom_button=False,
            public_builder=True,
            parts_library_filters=bom_builder_filter_options(session),
            initial_parts_library_parts=bom_builder_library_rows(session),
            format_bom_cost=format_bom_cost,
        )

    @app.route("/session-bom/<bom_uuid>/edit", methods=["GET", "POST"])
    def edit_session_bom_node_editor(bom_uuid):
        ensure_part_boms(session)
        record = get_session_bom_record(bom_uuid)
        if record is None:
            return _("BOM not found."), 404

        if request.method == "POST":
            if request.form.get("name", "").strip():
                update_session_bom_record(
                    bom_uuid,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    node_editor_payload_from_request(),
                )
            return redirect(url_for("boms"))

        edit_bom = get_session_bom(session, bom_uuid)
        return render_template(
            "admin/bom_node_editor.html",
            bom_options=get_bom_options(session),
            edit_bom=edit_bom,
            form_action=url_for("edit_session_bom_node_editor", bom_uuid=bom_uuid),
            table_editor_url=url_for("boms"),
            draft_storage_key=f"openpartslibrary:public-bom-node-editor:session:{bom_uuid}",
            initial_items=record.get("children", []),
            loadable_boms=[],
            show_load_bom_button=False,
            public_builder=True,
            parts_library_filters=bom_builder_filter_options(session),
            initial_parts_library_parts=bom_builder_library_rows(session),
            format_bom_cost=format_bom_cost,
        )

    @app.route("/bom/<int:bom_id>")
    def bom_view(bom_id):
        ensure_part_boms(session)
        bom = session.query(BillOfMaterials).filter_by(id=bom_id, is_part_wrapper=False).first()
        if bom is None:
            return _("BOM not found."), 404

        part_rows = sorted(
            bom_part_quantities(bom).values(),
            key=lambda row: (
                str(row["component"].number or "").lower() if row["component"] else "",
                str(row["component"].name or "").lower() if row["component"] else "",
            ),
        )

        return render_template(
            "bom.html",
            bom=bom,
            part_rows=part_rows,
            format_bom_cost=format_bom_cost,
            bom_has_cad_files=lambda bom: bom_has_cad_files(bom, cad_dir),
        )

    @app.route("/session-bom/<bom_uuid>")
    def session_bom_view(bom_uuid):
        ensure_part_boms(session)
        bom = get_session_bom(session, bom_uuid)
        if bom is None:
            return _("BOM not found."), 404

        part_rows = sorted(
            bom_part_quantities(bom).values(),
            key=lambda row: (
                str(row["component"].number or "").lower() if row["component"] else "",
                str(row["component"].name or "").lower() if row["component"] else "",
            ),
        )

        return render_template(
            "bom.html",
            bom=bom,
            part_rows=part_rows,
            format_bom_cost=format_bom_cost,
            bom_has_cad_files=lambda bom: bom_has_cad_files(bom, cad_dir),
        )

    def zip_download_response(bom, download_event_type, cad_item_event_type, default_name):
        """Create a CAD/SPDX ZIP response for a BOM-like object.

        :param bom: Persistent or session BOM to package.
        :param download_event_type: Download-event category for the ZIP file.
        :param cad_item_event_type: Download-event category for each CAD item.
        :param default_name: Fallback archive stem when the BOM has no name.
        :return: Flask response or ``(message, status)`` tuple.
        """

        zip_buffer = io.BytesIO()
        files_added = 0
        bom_components = []

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for row in bom_part_quantities(bom).values():
                component = row["component"]
                quantity = row["quantity"]
                if component is None:
                    continue

                archive_name = add_component_cad_to_zip(zip_file, component, cad_item_event_type)
                if archive_name:
                    files_added += 1

                bom_components.append(component_hbom_row(component, quantity, archive_name))

            write_hbom_manifest(zip_file, bom_components)

        if files_added == 0 and not bom_components:
            return _("No CAD files found for this BOM."), 404

        zip_buffer.seek(0)
        zip_download_name = branded_library_filename(f"{bom.number or bom.name or default_name}.zip")
        record_download_event(session, download_event_type, zip_download_name, quantity=1)
        return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=zip_download_name)

    def add_component_cad_to_zip(zip_file, component, download_event_type):
        """Add a component's CAD file to an open ZIP archive when available."""

        if component.cad_file is None:
            return None

        cad_path = parts_library.stored_cad_path(component)
        if cad_path is None or not cad_path.exists():
            return None

        part_number = component.number or component.uuid
        original_name = component.cad_file.name or cad_path.name
        archive_name = branded_part_filename(part_number, original_name)
        zip_file.write(cad_path, archive_name)
        record_download_event(
            session,
            download_event_type,
            archive_name,
            component=component,
            file=component.cad_file,
            quantity=1,
        )
        return archive_name

    def component_hbom_row(component, quantity, archive_name=None):
        """Convert a component and quantity into SPDX hardware BOM input."""

        return {
            "uuid": component.uuid,
            "name": component.name,
            "part_number": component.number,
            "quantity": quantity,
            "price_per_item": str(component.unit_price or ""),
            "currency": component.currency or "",
            "cad_file": archive_name,
            "description": component.description or "",
            "supplier": component.supplier.name if component.supplier else "",
        }

    def write_hbom_manifest(zip_file, bom_components):
        """Write the SPDX hardware BOM manifest into an archive."""

        if bom_components:
            zip_file.writestr(
                branded_library_filename("hardware-bom.spdx.jsonld"),
                json.dumps(build_spdx_hardware_bom(bom_components), indent=2),
            )

    @app.route("/bom/<int:bom_id>/download")
    def bom_download(bom_id):
        ensure_part_boms(session)
        bom = session.query(BillOfMaterials).filter_by(id=bom_id, is_part_wrapper=False).first()
        if bom is None:
            return _("BOM not found."), 404

        return zip_download_response(bom, "bom_zip", "bom_cad_item", "bom")

    @app.route("/session-bom/<bom_uuid>/download")
    def session_bom_download(bom_uuid):
        ensure_part_boms(session)
        bom = get_session_bom(session, bom_uuid)
        if bom is None:
            return _("BOM not found."), 404

        return zip_download_response(bom, "session_bom_zip", "session_bom_cad_item", "bom")

    @app.route("/component_view/<uuid>")
    def component_view(uuid):
        ensure_part_boms(session)
        component = session.query(Component).filter_by(uuid=uuid).first()
        if component is None:
            return _("Part not found with UUID: %(uuid)s", uuid=uuid), 404

        component_cad_filepath = None
        component_cad_filename = None
        if component.cad_file is not None:
            cad_path = parts_library.stored_cad_path(component)
            if cad_path is not None and cad_path.exists():
                component_cad_filepath = str(cad_path.resolve())
                component_cad_filename = cad_path.name

        used_in_boms = []
        for bom in get_created_boms(session):
            part_row = bom_part_quantities(bom).get(component.uuid)
            if part_row is None:
                continue
            used_in_boms.append({
                "bom": bom,
                "quantity": part_row["quantity"],
                "cost": format_bom_cost(bom),
            })

        return render_template(
            "component.html",
            component=component,
            len=len,
            component_cad_filepath=component_cad_filepath,
            component_cad_filename=component_cad_filename,
            files=component.files,
            used_in_files=[],
            used_in_boms=used_in_boms,
        )

    @app.route("/component/<uuid>/download-cad")
    def component_download_cad(uuid):
        component = session.query(Component).filter_by(uuid=uuid).first()
        if component is None or component.cad_file is None:
            return _("CAD file not found."), 404

        cad_path = parts_library.stored_cad_path(component)
        if cad_path is None or not cad_path.exists():
            return _("CAD file not found."), 404

        part_number = component.number or component.uuid
        original_name = component.cad_file.name or cad_path.name
        downloaded_filename = branded_part_filename(part_number, original_name)
        record_download_event(
            session,
            "component_cad",
            downloaded_filename,
            component=component,
            file=component.cad_file,
            quantity=1,
        )

        return send_file(cad_path, as_attachment=True, download_name=downloaded_filename)

    @app.route("/component/<uuid>/thumbnail")
    def component_thumbnail(uuid):
        component = session.query(Component).filter_by(uuid=uuid).first()
        if component is None or component.cad_file is None:
            return placeholder_thumbnail_response()

        return cad_thumbnail(component.cad_file.uuid, parts_library.stored_cad_path(component))

    @app.route("/thumbnail/cad/<cad_file_uuid>.png")
    def cad_thumbnail(cad_file_uuid, cad_path=None):
        result = ensure_cad_thumbnail(
            cad_file_uuid,
            cad_dir,
            mesh_dir,
            thumbnail_dir,
            app.config.get("FREECAD_3MF_EXPORT_COMMAND", ""),
            app.config.get("BLENDER_THUMBNAIL_COMMAND", ""),
            cad_path=cad_path,
        )
        if result.ready:
            return send_file(result.thumbnail_path, mimetype="image/png")

        return placeholder_thumbnail_response(result.message)

    def placeholder_thumbnail_response(message=None):
        label = _("No preview")
        response = app.response_class(
            placeholder_thumbnail_svg(label),
            mimetype="image/svg+xml",
        )
        response.headers["Cache-Control"] = "no-store"
        if message:
            response.headers["X-OpenPartsLibrary-Thumbnail-Status"] = message[:500]
        return response

    @app.route("/selection/download", methods=["POST"])
    def selection_download():
        selection_items = request.get_json(silent=True) or []
        if not isinstance(selection_items, list):
            return _("Expected a list of selected parts."), 400

        selected_quantities = selection_quantities_from_payload(selection_items)

        zip_buffer = io.BytesIO()
        files_added = 0
        bom_components = []

        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for component_uuid, quantity in selected_quantities.items():
                component = session.query(Component).filter_by(uuid=component_uuid).first()
                if component is None:
                    continue

                archive_name = add_component_cad_to_zip(zip_file, component, "selection_cad_item")
                if archive_name:
                    files_added += 1
                bom_components.append(component_hbom_row(component, quantity, archive_name))

            write_hbom_manifest(zip_file, bom_components)

        if files_added == 0 and not bom_components:
            return _("No CAD files found for My Bill of Materials."), 404

        zip_buffer.seek(0)
        zip_download_name = branded_library_filename("my-bill-of-materials.zip")
        record_download_event(session, "selection_zip", zip_download_name, quantity=1)
        return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=zip_download_name)

    @app.route("/selection/parts", methods=["POST"])
    def selection_parts():
        selection_items = request.get_json(silent=True) or []
        if not isinstance(selection_items, list):
            return jsonify([])

        components = []
        quantities_by_uuid = selection_quantities_from_payload(selection_items)

        for component_uuid, quantity in quantities_by_uuid.items():
            component = session.query(Component).filter_by(uuid=component_uuid).first()
            if component is None:
                continue

            has_cad = parts_library.stored_cad_path(component) is not None

            components.append({
                "uuid": component.uuid,
                "name": component.name,
                "part_number": component.number,
                "quantity": quantity,
                "price_per_item": str(component.unit_price or ""),
                "currency": component.currency or "",
                "has_cad": has_cad,
            })

        def selection_sort_value(component):
            try:
                return float(component["price_per_item"] or 0)
            except (TypeError, ValueError):
                return 0

        components.sort(key=selection_sort_value, reverse=True)

        return jsonify(components)

    @app.route("/selection/components", methods=["POST"])
    def legacy_selection_components_redirect():
        return redirect(url_for("selection_parts"), code=307)

    @app.route("/selection/bom-draft", methods=["POST"])
    def selection_bom_draft():
        ensure_part_boms(session)
        selection_items = request.get_json(silent=True) or []
        if not isinstance(selection_items, list):
            return jsonify({"error": _("Expected a list of selected parts.")}), 400

        nodes = selection_nodes_from_quantities(selection_quantities_from_payload(selection_items))
        return jsonify({
            "rootName": _("My Bill of Materials"),
            "rootDescription": "",
            "nodes": nodes,
            "savedAt": datetime.utcnow().isoformat(timespec="seconds"),
        })

    @app.route("/selection/save-bom", methods=["POST"])
    def selection_save_bom():
        ensure_part_boms(session)
        payload = request.get_json(silent=True) or {}
        selection_items = payload.get("items", []) if isinstance(payload, dict) else []
        if not isinstance(selection_items, list):
            return jsonify({"error": _("Expected a list of selected parts.")}), 400

        nodes = selection_nodes_from_quantities(selection_quantities_from_payload(selection_items))
        if not nodes:
            return jsonify({"error": _("No parts found in My Bill of Materials.")}), 400

        name = str(payload.get("name") or "").strip() if isinstance(payload, dict) else ""
        if not name:
            name = _("My Bill of Materials")
        record = save_session_bom_record(
            name,
            str(payload.get("description") or "").strip() if isinstance(payload, dict) else "",
            {"children": nodes},
        )
        if record is None:
            return jsonify({"error": _("BOM could not be saved.")}), 400
        return jsonify({"uuid": record["uuid"], "name": record["name"], "url": url_for("boms")})

    def selection_nodes_from_quantities(quantities_by_uuid):
        nodes = []
        for component_uuid, quantity in quantities_by_uuid.items():
            component = session.query(Component).filter_by(uuid=component_uuid).first()
            if component is None:
                continue
            part_bom = (
                session.query(BillOfMaterials)
                .filter_by(component_id=component.id, is_part_wrapper=True)
                .first()
            )
            if part_bom is None:
                continue
            display_label = f"{part_bom.number + ' - ' if part_bom.number else ''}{part_bom.name}"
            nodes.append({
                "child_bom_id": part_bom.id,
                "display_label": display_label,
                "source_type": "existing",
                "readonly": False,
                "new_bom_name": "",
                "new_bom_description": "",
                "quantity": str(quantity),
                "children": [],
            })
        return nodes

    @app.route("/file/download/<file_uuid>")
    def download_file(file_uuid):
        file = session.query(File).filter_by(uuid=file_uuid).first()
        if file is None:
            return _("File not found with UUID: %(uuid)s", uuid=file_uuid), 404

        matching_files = sorted(file_dir.glob(f"{file.uuid}.*"))
        if not matching_files:
            return _("File content not found."), 404

        source_file = matching_files[0]
        downloaded_filename = branded_library_filename(file.name or source_file.name)
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
            return _("CAD file not found."), 404
        filepath = url_for("serve_model_file", filename=filename)
        return render_template("viewer.html", filepath=filepath)

    @app.route("/static/cad/<filename>")
    def serve_model_file(filename):
        return send_from_directory(str(cad_dir), filename)
