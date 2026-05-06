import uuid
import json
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from flask import current_app, session as flask_session

from openpartslibrary.boms import decimal_quantity
from openpartslibrary.models import BillOfMaterials


SESSION_BOMS_ID_KEY = "user_created_boms_id"
SESSION_BOMS_DIRNAME = "session_boms"


def mark_session_boms_permanent():
    flask_session.permanent = True


def get_session_bom_records():
    mark_session_boms_permanent()
    records = read_session_bom_store()
    if not isinstance(records, list):
        return []
    return [record for record in records if isinstance(record, dict)]


def save_session_bom_record(name, description, payload):
    record = {
        "uuid": str(uuid.uuid4()),
        "name": str(name or "").strip(),
        "description": str(description or "").strip(),
        "children": sanitize_session_nodes((payload or {}).get("children", [])),
        "created_at": datetime.utcnow().isoformat(timespec="seconds"),
    }
    if not record["name"]:
        return None

    records = get_session_bom_records()
    records.insert(0, record)
    write_session_bom_store(records)
    flask_session.modified = True
    return record


def update_session_bom_record(bom_uuid, name, description, payload):
    records = get_session_bom_records()
    for index, record in enumerate(records):
        if record.get("uuid") != bom_uuid:
            continue

        updated_record = {
            **record,
            "name": str(name or "").strip(),
            "description": str(description or "").strip(),
            "children": sanitize_session_nodes((payload or {}).get("children", [])),
            "updated_at": datetime.utcnow().isoformat(timespec="seconds"),
        }
        if not updated_record["name"]:
            return None
        records[index] = updated_record
        write_session_bom_store(records)
        flask_session.modified = True
        return updated_record
    return None


def get_session_bom_record(bom_uuid):
    for record in get_session_bom_records():
        if record.get("uuid") == bom_uuid:
            return record
    return None


def get_session_boms_id():
    mark_session_boms_permanent()
    session_boms_id = flask_session.get(SESSION_BOMS_ID_KEY)
    if not session_boms_id:
        session_boms_id = str(uuid.uuid4())
        flask_session[SESSION_BOMS_ID_KEY] = session_boms_id
        flask_session.modified = True
    return session_boms_id


def session_boms_path():
    session_boms_id = get_session_boms_id()
    storage_dir = Path(current_app.instance_path) / SESSION_BOMS_DIRNAME
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir / f"{session_boms_id}.json"


def read_session_bom_store():
    path = session_boms_path()
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8") as handle:
            records = json.load(handle)
    except (OSError, ValueError):
        return []
    return records if isinstance(records, list) else []


def write_session_bom_store(records):
    path = session_boms_path()
    with path.open("w", encoding="utf-8") as handle:
        json.dump(records, handle)


def sanitize_session_nodes(nodes):
    sanitized_nodes = []
    for node in nodes or []:
        if not isinstance(node, dict):
            continue

        source_type = "new" if node.get("source_type") == "new" else "existing"
        sanitized_node = {
            "source_type": source_type,
            "quantity": str(decimal_quantity(node.get("quantity"))),
            "child_bom_id": "",
            "display_label": "",
            "new_bom_name": "",
            "new_bom_description": "",
            "children": [],
        }

        if source_type == "new":
            name = str(node.get("new_bom_name") or "").strip()
            if not name:
                continue
            sanitized_node["new_bom_name"] = name
            sanitized_node["new_bom_description"] = str(node.get("new_bom_description") or "").strip()
            sanitized_node["children"] = sanitize_session_nodes(node.get("children", []))
        else:
            child_bom_id = node.get("child_bom_id")
            if not child_bom_id:
                continue
            try:
                sanitized_node["child_bom_id"] = int(child_bom_id)
            except (TypeError, ValueError):
                continue
            sanitized_node["display_label"] = str(node.get("display_label") or "").strip()

        sanitized_nodes.append(sanitized_node)
    return sanitized_nodes


def get_session_boms(db_session):
    return [
        build_session_bom(db_session, record)
        for record in get_session_bom_records()
    ]


def get_session_bom(db_session, bom_uuid):
    for record in get_session_bom_records():
        if record.get("uuid") == bom_uuid:
            return build_session_bom(db_session, record)
    return None


def build_session_bom(db_session, record, path="root"):
    bom_uuid = record.get("uuid") or str(uuid.uuid4())
    return SimpleNamespace(
        id=f"session-{bom_uuid}-{path}",
        uuid=bom_uuid,
        number="",
        name=record.get("name") or "Session BOM",
        description=record.get("description") or "",
        is_part_wrapper=False,
        is_session_bom=True,
        component=None,
        children=build_session_items(db_session, record.get("children", []), bom_uuid, path),
    )


def build_session_items(db_session, nodes, bom_uuid, parent_path):
    items = []
    for position, node in enumerate(nodes or [], start=1):
        child_bom = resolve_session_child_bom(db_session, node, bom_uuid, f"{parent_path}-{position}")
        if child_bom is None:
            continue
        items.append(SimpleNamespace(
            id=f"session-item-{bom_uuid}-{parent_path}-{position}",
            parent_bom_id=f"session-{bom_uuid}-{parent_path}",
            child_bom_id=getattr(child_bom, "id", ""),
            child_bom=child_bom,
            quantity=decimal_quantity(node.get("quantity")),
            position=position,
        ))
    return items


def resolve_session_child_bom(db_session, node, bom_uuid, path):
    if node.get("source_type") == "new":
        return build_session_bom(
            db_session,
            {
                "uuid": f"{bom_uuid}-{path}",
                "name": node.get("new_bom_name") or "Session BOM",
                "description": node.get("new_bom_description") or "",
                "children": node.get("children", []),
            },
            path,
        )

    try:
        child_bom_id = int(node.get("child_bom_id"))
    except (TypeError, ValueError):
        return None
    return db_session.query(BillOfMaterials).filter_by(id=child_bom_id).first()
