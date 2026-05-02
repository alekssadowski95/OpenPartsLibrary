from pathlib import Path

from flask import request

from openpartslibrary.models import DownloadEvent


def with_openpartslibrary_suffix(filename):
    path = Path(filename)
    suffix = "".join(path.suffixes)
    stem = path.name[:-len(suffix)] if suffix else path.name
    if stem.endswith("_OpenPartsLibrary"):
        return path.name
    return f"{stem}_OpenPartsLibrary{suffix}"


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
