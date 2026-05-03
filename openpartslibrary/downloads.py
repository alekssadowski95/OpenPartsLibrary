from pathlib import Path

from flask import request

from openpartslibrary.models import DownloadEvent


def sanitize_filename_part(value):
    return str(value or "").replace("/", "-").replace("\\", "-").strip()


def branded_part_filename(part_number, original_name):
    part_number = sanitize_filename_part(part_number)
    original_name = sanitize_filename_part(original_name)
    original_path = Path(original_name)
    suffix = original_path.suffix
    original_stem = original_path.stem if suffix else original_path.name
    prefixed_part_number = f"OPL{part_number}" if part_number else "OPL"
    filename_stem = "_".join(part for part in (prefixed_part_number, original_stem, "OpenPartsLibrary", "www.alsado.de") if part)
    return f"{filename_stem}{suffix}"


def branded_library_filename(filename):
    filename = sanitize_filename_part(filename)
    return "_".join(part for part in ("OPL", "OpenPartsLibrary", filename) if part)


def record_download_event(
    session,
    download_type,
    downloaded_filename,
    component=None,
    file=None,
    quantity=None,
):
    event = DownloadEvent(
        download_type=download_type,
        component_uuid=component.uuid if component else None,
        component_name=component.name if component else None,
        component_number=component.number if component else None,
        file_uuid=file.uuid if file else None,
        file_name=file.name if file else None,
        downloaded_filename=downloaded_filename,
        quantity=quantity,
        user_id=None,
        remote_addr=request.remote_addr,
        user_agent=request.user_agent.string[:500] if request.user_agent else None,
    )
    session.add(event)
    session.commit()
