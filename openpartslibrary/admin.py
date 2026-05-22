"""Admin views, fallback admin pages, and BOM editor route helpers."""

import json
import math
import shutil
import tempfile
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

try:
    from flask_admin import Admin, AdminIndexView, expose
    from flask_admin.contrib.sqla import ModelView
    from flask_admin.menu import MenuLink
except ImportError:
    Admin = None
    AdminIndexView = None
    expose = None
    ModelView = None
    MenuLink = None

from flask import flash, redirect, render_template, request, send_file, url_for
from markupsafe import escape

from openpartslibrary.boms import copy_bom, create_bom, ensure_part_boms, format_bom_cost, get_bom_options, get_created_boms, replace_bom_items, update_bom
from openpartslibrary.i18n import gettext as _, lazy_gettext
from openpartslibrary.models import BillOfMaterials, BillOfMaterialsItem, Component, ComponentComponent, ComponentFile, DownloadEvent, File, Material, Supplier
from openpartslibrary.parts_package import PartsPackage


DOWNLOAD_DASHBOARD_TIMEFRAMES = {
    "7d": ("Last 7 days", 7),
    "30d": ("Last 30 days", 30),
    "90d": ("Last 90 days", 90),
    "365d": ("Last 12 months", 365),
    "all": ("All time", None),
}

ADMIN_SCRIPT_DEFINITIONS = (
    {
        "id": "import_sample_parts_package",
        "name": "Import sample parts package",
        "description": "Pick one or more bundled sample packages to import.",
        "button_label": "Choose packages",
        "icon": "bi-box-arrow-in-down",
        "modal_target": "samplePackagesModal",
    },
    {
        "id": "export_parts_package",
        "name": "Export parts package",
        "description": "Download the current library as a parts package zip.",
        "button_label": "Run export",
        "icon": "bi-box-arrow-up",
    },
    {
        "id": "import_parts_package",
        "name": "Import parts package",
        "description": "Upload and import a parts package zip.",
        "button_label": "Import package",
        "icon": "bi-upload",
        "file_field": "package_file",
        "file_accept": ".zip",
    },
    {
        "id": "delete_system_boms",
        "name": "Delete all system BOMs",
        "description": "Delete generated part-wrapper BOM records.",
        "button_label": "Run delete",
        "icon": "bi-trash",
        "button_class": "btn-outline-danger",
        "confirmation": "This will delete all generated system BOMs. Parts will remain.",
    },
    {
        "id": "delete_user_boms",
        "name": "Delete all user BOMs",
        "description": "Delete user-created BOM records and their BOM relations.",
        "button_label": "Run delete",
        "icon": "bi-trash",
        "button_class": "btn-outline-danger",
        "confirmation": "This will delete all user-created BOMs and their BOM relations. Parts will remain.",
    },
    {
        "id": "delete_parts",
        "name": "Delete all parts",
        "description": "Delete all parts and generated part-wrapper BOMs.",
        "button_label": "Run delete",
        "icon": "bi-trash",
        "button_class": "btn-outline-danger",
        "confirmation": "This will delete all parts, part relations, component-file links, and generated system BOMs.",
    },
    {
        "id": "delete_all_data",
        "name": "Delete all data",
        "description": "Delete all library records, events, and runtime data files.",
        "button_label": "Run delete",
        "icon": "bi-trash",
        "button_class": "btn-danger",
        "confirmation": "This will delete all library records, events, and runtime data files.",
    },
)


def get_admin_script_definitions():
    """Return translated admin script metadata."""

    return [
        {
            **script,
            "name": _(script["name"]),
            "description": _(script["description"]),
            "button_label": _(script["button_label"]),
            "button_class": script.get("button_class", "btn-primary"),
            "confirmation": _(script["confirmation"]) if script.get("confirmation") else None,
        }
        for script in ADMIN_SCRIPT_DEFINITIONS
    ]


def get_sample_parts_packages(parts_library):
    """Return package zip files available in the bundled sample folder."""

    sample_dir_path = parts_library.sample_data_dir_path
    if not sample_dir_path.exists():
        return []

    return [
        {
            "name": package_path.name,
            "size_kb": max(1, round(package_path.stat().st_size / 1024)),
            "modified": datetime.fromtimestamp(package_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        }
        for package_path in sorted(sample_dir_path.glob("*.zip"), key=lambda path: path.name.lower())
        if package_path.is_file()
    ]


def download_event_quantity(event):
    """Return the quantity contribution for one download event."""

    return 1


def download_part_key(event):
    """Return the grouping key for per-part download analytics."""

    if not event.component_uuid:
        return None
    return (
        event.component_uuid,
        event.component_number or "",
        event.component_name or _("Unknown part"),
    )


def get_download_dashboard_data(session, timeframe_key):
    """Build chart and ranking data for the downloads dashboard.

    :param session: SQLAlchemy session.
    :param timeframe_key: Selected timeframe key such as ``30d`` or ``all``.
    :return: Dashboard data dictionary for templates.
    :rtype: dict
    """

    timeframe_key = timeframe_key if timeframe_key in DOWNLOAD_DASHBOARD_TIMEFRAMES else "30d"
    timeframe_label, timeframe_days = DOWNLOAD_DASHBOARD_TIMEFRAMES[timeframe_key]
    now = datetime.utcnow()
    start_date = now - timedelta(days=timeframe_days) if timeframe_days else None

    query = session.query(DownloadEvent)
    if start_date is not None:
        query = query.filter(DownloadEvent.date_downloaded >= start_date)
    events = query.order_by(DownloadEvent.date_downloaded.asc()).all()

    chart_counts = defaultdict(int)
    part_counts = defaultdict(lambda: {"part_number": "", "part_name": "", "count": 0})
    recent_counts = defaultdict(lambda: {"part_number": "", "part_name": "", "count": 0})
    previous_counts = defaultdict(lambda: {"part_number": "", "part_name": "", "count": 0})

    if timeframe_days:
        recent_window_days = max(1, min(14, timeframe_days // 2))
    else:
        recent_window_days = 30
    recent_start = now - timedelta(days=recent_window_days)
    previous_start = recent_start - timedelta(days=recent_window_days)

    for event in events:
        quantity = download_event_quantity(event)
        chart_counts[event.date_downloaded.date().isoformat()] += quantity

        part_key = download_part_key(event)
        if part_key is None:
            continue

        component_uuid, part_number, part_name = part_key
        part_counts[component_uuid]["part_number"] = part_number
        part_counts[component_uuid]["part_name"] = part_name
        part_counts[component_uuid]["count"] += quantity

        if event.date_downloaded >= recent_start:
            recent_counts[component_uuid]["part_number"] = part_number
            recent_counts[component_uuid]["part_name"] = part_name
            recent_counts[component_uuid]["count"] += quantity
        elif event.date_downloaded >= previous_start:
            previous_counts[component_uuid]["part_number"] = part_number
            previous_counts[component_uuid]["part_name"] = part_name
            previous_counts[component_uuid]["count"] += quantity

    if timeframe_days:
        chart_start = start_date.date()
        chart_labels = [
            (chart_start + timedelta(days=day_offset)).isoformat()
            for day_offset in range(timeframe_days + 1)
        ]
    else:
        chart_labels = sorted(chart_counts)

    chart_values = [chart_counts[label] for label in chart_labels]

    most_downloaded = sorted(
        part_counts.values(),
        key=lambda row: (-row["count"], row["part_name"].lower()),
    )[:10]

    trending_rows = []
    for component_uuid, recent_row in recent_counts.items():
        recent_count = recent_row["count"]
        previous_count = previous_counts[component_uuid]["count"]
        absolute_increase = recent_count - previous_count
        if recent_count <= 0 or absolute_increase <= 0:
            continue

        percent_increase = (absolute_increase / max(previous_count, 1)) * 100
        trend_score = absolute_increase * math.log1p(recent_count) + percent_increase
        trending_rows.append({
            "part_number": recent_row["part_number"],
            "part_name": recent_row["part_name"],
            "recent_count": recent_count,
            "previous_count": previous_count,
            "absolute_increase": absolute_increase,
            "percent_increase": percent_increase,
            "trend_score": trend_score,
        })

    trending_rows.sort(key=lambda row: (-row["trend_score"], -row["absolute_increase"], row["part_name"].lower()))

    return {
        "timeframe_key": timeframe_key,
        "timeframe_label": timeframe_label,
        "timeframes": DOWNLOAD_DASHBOARD_TIMEFRAMES,
        "translated_timeframes": {
            key: (_(label), days)
            for key, (label, days) in DOWNLOAD_DASHBOARD_TIMEFRAMES.items()
        },
        "total_downloads": sum(chart_values),
        "total_part_downloads": sum(row["count"] for row in part_counts.values()),
        "chart_labels": chart_labels,
        "chart_values": chart_values,
        "most_downloaded": most_downloaded,
        "trending": trending_rows[:10],
        "recent_window_days": recent_window_days,
    }


def render_bom_row(bom, depth=0, visited=None, relation_quantity=None):
    """Render one expandable BOM row for the admin BOM tree table."""

    visited = set(visited or set())
    children_id = f"bom-children-{bom.id}-{depth}"
    child_rows = []
    if bom.id not in visited:
        next_visited = visited | {bom.id}
        for item in sorted(bom.children, key=lambda child: (child.position, child.id)):
            child_rows.append(render_bom_item_row(item, depth + 1, next_visited))

    can_expand = bool(child_rows)
    expand_button = (
        f'<button class="bom-expand-button" type="button" aria-expanded="false" aria-controls="{children_id}" aria-label="{escape(_("Expand BOM"))}"></button>'
        if can_expand
        else '<span class="d-inline-block" style="width:30px;"></span>'
    )
    number = escape(bom.number or "")
    kind = _("Part") if bom.is_part_wrapper else _("BOM")
    row_icon = (
        '<i class="bi bi-box-fill bom-list-icon bom-list-icon-part" aria-hidden="true"></i>'
        if bom.is_part_wrapper
        else '<i class="bi bi-table bom-list-icon" aria-hidden="true"></i>'
    )
    number_label = f'<span class="bom-list-number">{number}</span>' if number else ""
    quantity_label = escape(relation_quantity) if relation_quantity is not None else "-"
    children = f'<div id="{children_id}" class="bom-child-list">{"".join(child_rows)}</div>' if can_expand else ""
    row_click = f' onclick="toggleBomChildrenForRow(event, \'{children_id}\')"' if can_expand else ""
    actions = ""
    if bom.is_part_wrapper and bom.component:
        actions = f"""
            <div class="bom-list-actions">
                <a class="btn btn-sm btn-outline-secondary" href="{url_for("component_view", uuid=bom.component.uuid)}" onclick="event.stopPropagation()" title="{escape(_("Part details"))}" aria-label="{escape(_("Part details"))}"><i class="bi bi-eye"></i></a>
            </div>
        """
    elif not bom.is_part_wrapper:
        download_action = (
            f'<a class="btn btn-sm btn-outline-secondary" href="{url_for("bom_download", bom_id=bom.id)}" onclick="event.stopPropagation()" title="{escape(_("Download"))}" aria-label="{escape(_("Download"))}"><i class="bi bi-download"></i></a>'
            if depth == 0
            else ""
        )
        edit_actions = (
            f"""
                <a class="btn btn-sm btn-outline-secondary" href="{url_for("admin_edit_bom_node_editor", bom_id=bom.id)}" onclick="event.stopPropagation()" title="{escape(_("Modify BOM"))}" aria-label="{escape(_("Modify BOM"))}"><i class="bi bi-pencil-square"></i></a>
                <form method="post" action="{url_for("admin_copy_bom", bom_id=bom.id)}" onclick="event.stopPropagation()">
                    <button class="btn btn-sm btn-outline-secondary" type="submit" title="{escape(_("Copy"))}" aria-label="{escape(_("Copy"))}"><i class="bi bi-copy"></i></button>
                </form>
            """
            if depth == 0
            else ""
        )
        actions = f"""
            <div class="bom-list-actions">
                <a class="btn btn-sm btn-outline-secondary" href="{url_for("bom_view", bom_id=bom.id)}" onclick="event.stopPropagation()" title="{escape(_("BOM details"))}" aria-label="{escape(_("BOM details"))}"><i class="bi bi-eye"></i></a>
                {download_action}
                {edit_actions}
            </div>
        """
    else:
        actions = '<span></span>'
    return f"""
    <div class="bom-list-row">
        <div class="bom-list-main {'bom-row-part' if bom.is_part_wrapper else 'bom-row-bom'} bom-level-{min(depth, 7)} {'is-expandable' if can_expand else ''}" style="padding-left: {12 + (depth * 22)}px !important;"{row_click}>
            {expand_button}
            <div class="bom-list-name">
                {row_icon}
                {number_label}
                <span class="fw-semibold">{escape(bom.name)}</span>
                <span class="bom-list-meta">{escape(kind)}</span>
            </div>
            <div class="text-end bom-list-quantity">{quantity_label}</div>
            <div class="text-end bom-list-cost">{escape(format_bom_cost(bom))}</div>
            {actions}
        </div>
        {children}
    </div>
    """


def render_bom_item_row(item, depth, visited):
    """Render a child BOM item row by delegating to :func:`render_bom_row`."""

    quantity = item.quantity.normalize() if item.quantity else 1
    return render_bom_row(item.child_bom, depth, visited, quantity)


def bom_form_items_from_request():
    """Parse flat BOM child item form fields from the current request."""

    item_ids = request.form.getlist("child_bom_id")
    quantities = request.form.getlist("quantity")
    return [
        {
            "child_bom_id": item_id,
            "quantity": quantities[index] if index < len(quantities) else 1,
        }
        for index, item_id in enumerate(item_ids)
        if item_id
    ]


def initial_bom_items(bom, bom_options):
    """Serialize current child BOM rows for the classic table editor."""

    labels_by_id = {option["id"]: option["display_label"] for option in bom_options}
    return [
        {
            "child_bom_id": item.child_bom_id,
            "display_label": labels_by_id.get(item.child_bom_id, ""),
            "quantity": str(item.quantity.normalize() if item.quantity else 1),
        }
        for item in sorted(bom.children, key=lambda child: (child.position, child.id))
    ]


def initial_bom_tree_items(bom, bom_options, visited=None, readonly=False):
    """Serialize a nested BOM tree for the node editor."""

    visited = set(visited or set())
    labels_by_id = {option["id"]: option["display_label"] for option in bom_options}
    tree_items = []
    for item in sorted(bom.children, key=lambda child: (child.position, child.id)):
        child_bom = item.child_bom
        children = []
        if child_bom and not child_bom.is_part_wrapper and child_bom.id not in visited:
            children = initial_bom_tree_items(child_bom, bom_options, visited | {bom.id}, readonly=True)
        tree_items.append({
            "child_bom_id": item.child_bom_id,
            "display_label": labels_by_id.get(item.child_bom_id, ""),
            "source_type": "existing",
            "readonly": readonly,
            "new_bom_name": "",
            "new_bom_description": "",
            "quantity": str(item.quantity.normalize() if item.quantity else 1),
            "children": children,
        })
    return tree_items


def node_editor_payload_from_request():
    """Parse the JSON node tree submitted by the BOM node editor."""

    try:
        payload = json.loads(request.form.get("node_tree") or "{}")
    except (TypeError, ValueError):
        payload = {}
    return payload if isinstance(payload, dict) else {}


def resolve_node_editor_child_bom(session, node):
    """Resolve an editor node to an existing or newly created child BOM."""

    if not isinstance(node, dict):
        return None

    if node.get("source_type") == "new":
        name = str(node.get("new_bom_name") or "").strip()
        if not name:
            return None
        return create_bom(
            session,
            name,
            node.get("new_bom_description", ""),
            [],
        )

    child_bom_id = node.get("child_bom_id")
    if not child_bom_id:
        return None
    try:
        return session.query(BillOfMaterials).filter_by(id=int(child_bom_id)).first()
    except (TypeError, ValueError):
        return None


def save_nested_bom_nodes(session, parent_bom, nodes, visited=None):
    """Persist nested node-editor children under a parent BOM."""

    visited = set(visited or set())
    if parent_bom is None or parent_bom.id in visited:
        return

    next_visited = visited | {parent_bom.id}
    resolved_items = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue
        child_bom = resolve_node_editor_child_bom(session, node)
        if child_bom is None or child_bom.id in visited:
            continue
        if node.get("source_type") != "new" or child_bom.is_part_wrapper:
            node["children"] = []
        else:
            save_nested_bom_nodes(session, child_bom, node.get("children", []), next_visited)
        resolved_items.append({
            "child_bom_id": child_bom.id,
            "quantity": node.get("quantity", 1),
        })

    replace_bom_items(session, parent_bom, resolved_items)
    session.flush()


def save_node_editor_bom(session, bom, name, description, payload):
    """Update one BOM from the node editor payload and commit it."""

    bom.name = str(name or "").strip()
    bom.description = str(description or "").strip() or None
    save_nested_bom_nodes(session, bom, payload.get("children", []))
    session.commit()
    return bom


def register_bom_admin_routes(app, session):
    """Register custom BOM admin routes when they are not already present."""

    if "admin_bill_of_materials" in app.view_functions:
        return

    @app.route("/admin/bill-of-materials", methods=["GET", "POST"])
    def admin_bill_of_materials():
        ensure_part_boms(session)
        if request.method == "POST":
            items = bom_form_items_from_request()
            if request.form.get("name", "").strip():
                create_bom(
                    session,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    items,
                )
            return redirect(url_for("admin_bill_of_materials"))

        return render_template(
            "admin/bom_builder.html",
            boms=get_created_boms(session),
            bom_options=get_bom_options(session),
            edit_bom=None,
            form_action=url_for("admin_bill_of_materials"),
            node_editor_url=url_for("admin_bom_node_editor"),
            initial_items=[],
            render_bom_row=render_bom_row,
        )

    @app.route("/admin/bill-of-materials/node-editor", methods=["GET", "POST"])
    def admin_bom_node_editor():
        ensure_part_boms(session)
        if request.method == "POST":
            redirect_after_save = request.form.get("redirect_after_save", "")
            if request.form.get("name", "").strip():
                bom = create_bom(
                    session,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    [],
                )
                save_node_editor_bom(
                    session,
                    bom,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    node_editor_payload_from_request(),
                )
                if redirect_after_save.startswith("/admin/bill-of-materials/"):
                    return redirect(redirect_after_save)
            return redirect(url_for("admin_bill_of_materials"))

        return render_template(
            "admin/bom_node_editor.html",
            bom_options=get_bom_options(session),
            edit_bom=None,
            form_action=url_for("admin_bom_node_editor"),
            table_editor_url=url_for("admin_bill_of_materials"),
            draft_storage_key="openpartslibrary:bom-node-editor:new",
            initial_items=[],
            loadable_boms=get_created_boms(session),
            format_bom_cost=format_bom_cost,
        )

    @app.route("/admin/bill-of-materials/<int:bom_id>/copy", methods=["POST"])
    def admin_copy_bom(bom_id):
        ensure_part_boms(session)
        bom = session.query(BillOfMaterials).filter_by(id=bom_id, is_part_wrapper=False).first()
        if bom is None:
            return _("BOM not found."), 404
        copied_bom = copy_bom(session, bom)
        return redirect(url_for("admin_edit_bom", bom_id=copied_bom.id))

    @app.route("/admin/bill-of-materials/<int:bom_id>/node-editor", methods=["GET", "POST"])
    def admin_edit_bom_node_editor(bom_id):
        ensure_part_boms(session)
        bom = session.query(BillOfMaterials).filter_by(id=bom_id, is_part_wrapper=False).first()
        if bom is None:
            return _("BOM not found."), 404
        if request.method == "POST":
            redirect_after_save = request.form.get("redirect_after_save", "")
            if request.form.get("name", "").strip():
                save_node_editor_bom(
                    session,
                    bom,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    node_editor_payload_from_request(),
                )
                if redirect_after_save.startswith("/admin/bill-of-materials/"):
                    return redirect(redirect_after_save)
            return redirect(url_for("admin_bill_of_materials"))

        bom_options = [
            option for option in get_bom_options(session)
            if option["id"] != bom.id
        ]
        return render_template(
            "admin/bom_node_editor.html",
            bom_options=bom_options,
            edit_bom=bom,
            form_action=url_for("admin_edit_bom_node_editor", bom_id=bom.id),
            table_editor_url=url_for("admin_edit_bom", bom_id=bom.id),
            draft_storage_key=f"openpartslibrary:bom-node-editor:edit:{bom.id}",
            initial_items=initial_bom_tree_items(bom, bom_options),
            loadable_boms=get_created_boms(session),
            format_bom_cost=format_bom_cost,
        )

    @app.route("/admin/bill-of-materials/<int:bom_id>/edit", methods=["GET", "POST"])
    def admin_edit_bom(bom_id):
        ensure_part_boms(session)
        bom = session.query(BillOfMaterials).filter_by(id=bom_id, is_part_wrapper=False).first()
        if bom is None:
            return _("BOM not found."), 404
        if request.method == "POST":
            if request.form.get("name", "").strip():
                update_bom(
                    session,
                    bom,
                    request.form.get("name"),
                    request.form.get("description", ""),
                    bom_form_items_from_request(),
                )
            return redirect(url_for("admin_bill_of_materials"))

        bom_options = [
            option for option in get_bom_options(session)
            if option["id"] != bom.id
        ]
        return render_template(
            "admin/bom_builder.html",
            boms=[],
            bom_options=bom_options,
            edit_bom=bom,
            form_action=url_for("admin_edit_bom", bom_id=bom.id),
            node_editor_url=url_for("admin_edit_bom_node_editor", bom_id=bom.id),
            initial_items=initial_bom_items(bom, bom_options),
            render_bom_row=render_bom_row,
        )


def delete_boms_by_system_flag(session, is_system_bom):
    """Delete generated system BOMs or user-created BOMs."""

    bom_ids = [
        bom_id
        for (bom_id,) in (
            session.query(BillOfMaterials.id)
            .filter(BillOfMaterials.is_part_wrapper.is_(is_system_bom))
            .all()
        )
    ]
    if not bom_ids:
        return 0

    session.query(BillOfMaterialsItem).filter(BillOfMaterialsItem.parent_bom_id.in_(bom_ids)).delete(synchronize_session=False)
    session.query(BillOfMaterialsItem).filter(BillOfMaterialsItem.child_bom_id.in_(bom_ids)).delete(synchronize_session=False)
    deleted_count = (
        session.query(BillOfMaterials)
        .filter(BillOfMaterials.id.in_(bom_ids))
        .delete(synchronize_session=False)
    )
    session.commit()
    return deleted_count


def delete_all_parts(session):
    """Delete all parts and direct part relation records."""

    delete_boms_by_system_flag(session, True)
    session.query(ComponentComponent).delete(synchronize_session=False)
    session.query(ComponentFile).delete(synchronize_session=False)
    deleted_count = session.query(Component).delete(synchronize_session=False)
    session.commit()
    return deleted_count


def clear_runtime_data_files(parts_library):
    """Remove runtime files while preserving the expected data directories."""

    deleted_count = 0
    for data_dir_path in (
        parts_library.data_cad_dir_path,
        parts_library.data_files_dir_path,
        parts_library.data_dir_path / "mesh",
        parts_library.data_dir_path / "thumbnails",
    ):
        if not data_dir_path.exists():
            data_dir_path.mkdir(parents=True, exist_ok=True)
            continue

        for child_path in data_dir_path.iterdir():
            if child_path.is_dir():
                shutil.rmtree(child_path)
            else:
                child_path.unlink()
            deleted_count += 1
    return deleted_count


def delete_all_library_data(parts_library):
    """Delete all application records and runtime files."""

    session = parts_library.session
    deleted_counts = {
        "bom_items": session.query(BillOfMaterialsItem).delete(synchronize_session=False),
        "boms": session.query(BillOfMaterials).delete(synchronize_session=False),
        "part_relations": session.query(ComponentComponent).delete(synchronize_session=False),
        "component_files": session.query(ComponentFile).delete(synchronize_session=False),
        "parts": session.query(Component).delete(synchronize_session=False),
        "files": session.query(File).delete(synchronize_session=False),
        "suppliers": session.query(Supplier).delete(synchronize_session=False),
        "materials": session.query(Material).delete(synchronize_session=False),
        "download_events": session.query(DownloadEvent).delete(synchronize_session=False),
    }
    session.commit()
    deleted_counts["runtime_files"] = clear_runtime_data_files(parts_library)
    return deleted_counts


def register_admin_script_routes(app, parts_library):
    """Register admin script routes for package import/export operations."""

    if "admin_scripts" in app.view_functions:
        return

    package_interface = PartsPackage(parts_library)

    @app.route("/admin/scripts", methods=["GET"])
    def admin_scripts():
        return render_template(
            "admin/scripts.html",
            scripts=get_admin_script_definitions(),
            sample_packages=get_sample_parts_packages(parts_library),
        )

    @app.route("/admin/scripts/<script_id>/run", methods=["POST"])
    def admin_run_script(script_id):
        if script_id == "import_sample_parts_package":
            available_packages = {
                package["name"]: parts_library.sample_data_dir_path / package["name"]
                for package in get_sample_parts_packages(parts_library)
            }
            selected_package_names = request.form.getlist("sample_packages")
            selected_package_paths = [
                available_packages[package_name]
                for package_name in selected_package_names
                if package_name in available_packages
            ]
            if not selected_package_paths:
                flash(_("Choose at least one sample parts package to import."), "warning")
                return redirect(url_for("admin_scripts"))

            imported_count = 0
            skipped_count = 0
            imported_packages = 0
            failed_packages = []
            for sample_package_path in selected_package_paths:
                try:
                    import_result = package_interface.import_zip(sample_package_path)
                    imported_count += import_result.imported_parts_count
                    skipped_count += import_result.skipped_existing_uuid_count
                    imported_packages += 1
                except Exception as exc:
                    failed_packages.append(f"{sample_package_path.name}: {exc}")

            if imported_packages:
                ensure_part_boms(parts_library.session)
                flash(
                    _(
                        "Imported %(packages)d sample packages. %(imported)d parts imported, %(skipped)d skipped because their UUID already exists.",
                        packages=imported_packages,
                        imported=imported_count,
                        skipped=skipped_count,
                    ),
                    "success",
                )
            if failed_packages:
                flash(_("Sample package import failed: %(error)s", error="; ".join(failed_packages)), "danger")
            return redirect(url_for("admin_scripts"))

        if script_id == "export_parts_package":
            try:
                export_path = package_interface.export_zip()
            except Exception as exc:
                flash(_("Parts package export failed: %(error)s", error=str(exc)), "danger")
                return redirect(url_for("admin_scripts"))
            return send_file(
                export_path,
                as_attachment=True,
                download_name=Path(export_path).name,
                mimetype="application/zip",
            )

        if script_id == "import_parts_package":
            package_file = request.files.get("package_file")
            if package_file is None or not package_file.filename:
                flash(_("Choose a parts package zip to import."), "warning")
                return redirect(url_for("admin_scripts"))

            suffix = Path(package_file.filename).suffix.lower()
            if suffix != ".zip":
                flash(_("Parts packages must be zip files."), "danger")
                return redirect(url_for("admin_scripts"))

            with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as temp_file:
                temp_path = Path(temp_file.name)
                package_file.save(temp_file)

            try:
                import_result = package_interface.import_zip(temp_path)
                ensure_part_boms(parts_library.session)
                flash(
                    _(
                        "Parts package imported. %(imported)d parts imported, %(skipped)d skipped because their UUID already exists.",
                        imported=import_result.imported_parts_count,
                        skipped=import_result.skipped_existing_uuid_count,
                    ),
                    "success",
                )
            except Exception as exc:
                flash(_("Parts package import failed: %(error)s", error=str(exc)), "danger")
            finally:
                temp_path.unlink(missing_ok=True)
            return redirect(url_for("admin_scripts"))

        if script_id == "delete_system_boms":
            deleted_count = delete_boms_by_system_flag(parts_library.session, True)
            flash(_("Deleted %(count)d system BOMs.", count=deleted_count), "success")
            return redirect(url_for("admin_scripts"))

        if script_id == "delete_user_boms":
            deleted_count = delete_boms_by_system_flag(parts_library.session, False)
            flash(_("Deleted %(count)d user BOMs.", count=deleted_count), "success")
            return redirect(url_for("admin_scripts"))

        if script_id == "delete_parts":
            deleted_count = delete_all_parts(parts_library.session)
            flash(_("Deleted %(count)d parts.", count=deleted_count), "success")
            return redirect(url_for("admin_scripts"))

        if script_id == "delete_all_data":
            deleted_counts = delete_all_library_data(parts_library)
            flash(
                _(
                    "Deleted all data: %(parts)d parts, %(boms)d BOMs, %(files)d files, %(suppliers)d suppliers, %(events)d events, and %(runtime_files)d runtime files.",
                    parts=deleted_counts["parts"],
                    boms=deleted_counts["boms"],
                    files=deleted_counts["files"],
                    suppliers=deleted_counts["suppliers"],
                    events=deleted_counts["download_events"],
                    runtime_files=deleted_counts["runtime_files"],
                ),
                "success",
            )
            return redirect(url_for("admin_scripts"))

        return _("Admin script not found."), 404


def setup_admin(app, parts_library):
    """Install Flask-Admin views or fallback admin routes.

    :param app: Flask application.
    :param parts_library: Initialized :class:`openpartslibrary.db.PartsLibrary`.
    :return: Flask-Admin instance or fallback marker dictionary.
    """

    session = parts_library.session
    register_bom_admin_routes(app, session)
    register_admin_script_routes(app, parts_library)

    if Admin is None or ModelView is None:
        return setup_fallback_admin(app, session)

    class DownloadEventAdminView(ModelView):
        """Read-only Flask-Admin view for download audit events."""

        can_create = False
        can_edit = False
        can_delete = False
        column_default_sort = ("date_downloaded", True)
        column_list = (
            "date_downloaded",
            "download_type",
            "component_number",
            "component_name",
            "file_name",
            "downloaded_filename",
            "quantity",
            "remote_addr",
        )
        column_searchable_list = (
            "download_type",
            "component_number",
            "component_name",
            "file_name",
            "downloaded_filename",
            "remote_addr",
        )
        column_filters = ("download_type", "date_downloaded", "component_number")

    class ComponentAdminView(ModelView):
        """Flask-Admin model view for component records."""

        column_labels = {
            "unit_price": lazy_gettext("Estimated unit price"),
        }

    class DownloadsDashboardIndexView(AdminIndexView):
        """Custom Flask-Admin index page showing download analytics."""

        @expose("/")
        def index(self):
            """Render the downloads dashboard."""

            data = get_download_dashboard_data(session, request.args.get("timeframe", "30d"))
            return render_template(
                "admin/downloads_dashboard.html",
                data=data,
                dashboard_url=url_for(".index"),
                admin_home_url=url_for("admin.index"),
            )

    try:
        admin = Admin(app, name=lazy_gettext("OpenPartsLibrary Admin"), template_mode="bootstrap4", url="/admin", index_view=DownloadsDashboardIndexView(name=lazy_gettext("Downloads Dashboard"), endpoint="admin", url="/admin"))
    except TypeError:
        admin = Admin(app, name=lazy_gettext("OpenPartsLibrary Admin"), url="/admin", index_view=DownloadsDashboardIndexView(name=lazy_gettext("Downloads Dashboard"), endpoint="admin", url="/admin"))
    admin.add_view(ComponentAdminView(Component, session, name=lazy_gettext("Parts"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(File, session, name=lazy_gettext("Files"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(Supplier, session, name=lazy_gettext("Suppliers"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(Material, session, name=lazy_gettext("Materials"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(ComponentComponent, session, name=lazy_gettext("Part relations"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(BillOfMaterials, session, name=lazy_gettext("BOM records"), category=lazy_gettext("Library")))
    admin.add_view(ModelView(BillOfMaterialsItem, session, name=lazy_gettext("BOM relations"), category=lazy_gettext("Library")))
    admin.add_view(DownloadEventAdminView(DownloadEvent, session, name=lazy_gettext("Download events"), category=lazy_gettext("Events")))
    if MenuLink is not None:
        admin.add_link(MenuLink(name=lazy_gettext("Scripts"), category=lazy_gettext("Tools"), url="/admin/scripts"))
    return admin


def setup_fallback_admin(app, session):
    """Register read-only fallback admin pages when Flask-Admin is unavailable."""

    model_links = (
        ("Downloads dashboard", None),
        ("Scripts", None),
        ("Bill of Materials", None),
        ("Parts", Component),
        ("Files", File),
        ("Suppliers", Supplier),
        ("Materials", Material),
        ("Part relations", ComponentComponent),
        ("Download events", DownloadEvent),
    )

    @app.route("/admin")
    def fallback_admin_index():
        rows = [
            {
                "name": _(name),
                "count": session.query(model).count() if model is not None else None,
                "url": (
                    url_for("fallback_admin_downloads_dashboard")
                    if name == "Downloads dashboard"
                    else url_for("admin_scripts")
                    if name == "Scripts"
                    else url_for("admin_bill_of_materials")
                    if name == "Bill of Materials"
                    else url_for("fallback_admin_model", model_name=model.__tablename__)
                ),
            }
            for name, model in model_links
        ]
        return render_template(
            "admin/fallback_index.html",
            rows=rows,
        )

    @app.route("/admin/downloads-dashboard")
    def fallback_admin_downloads_dashboard():
        data = get_download_dashboard_data(session, request.args.get("timeframe", "30d"))
        return render_template(
            "admin/downloads_dashboard.html",
            data=data,
            dashboard_url=url_for("fallback_admin_downloads_dashboard"),
            admin_home_url=url_for("fallback_admin_index"),
        )

    @app.route("/admin/<model_name>")
    def fallback_admin_model(model_name):
        models_by_table = {
            model.__tablename__: (name, model)
            for name, model in model_links
            if model is not None
        }
        model_info = models_by_table.get(model_name)
        if model_info is None:
            return _("Admin model not found."), 404

        name, model = model_info
        columns = [column.name for column in model.__table__.columns]
        column_labels = {
            "unit_price": _("Estimated unit price"),
        }
        records = session.query(model).limit(200).all()
        return render_template(
            "admin/fallback_model.html",
            name=name,
            columns=columns,
            column_labels=column_labels,
            records=records,
        )

    return {"fallback": True}
