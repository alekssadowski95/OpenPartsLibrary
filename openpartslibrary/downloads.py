"""Download filename branding and event recording helpers."""

from pathlib import Path

from flask import request

from openpartslibrary.models import DownloadEvent


def sanitize_filename_part(value):
    """Return a filesystem-friendly filename segment.

    :param value: Raw filename segment or ``None``.
    :return: Sanitized string with path separators removed.
    :rtype: str
    """

    return str(value or "").replace("/", "-").replace("\\", "-").strip()


def branded_part_filename(part_number, original_name):
    """Build the public download name for an individual part file.

    :param part_number: Component number used for the OPL prefix.
    :param original_name: Original CAD or attachment filename.
    :return: Branded filename preserving the original suffix.
    :rtype: str
    """

    part_number = sanitize_filename_part(part_number)
    original_name = sanitize_filename_part(original_name)
    original_path = Path(original_name)
    suffix = original_path.suffix
    original_stem = original_path.stem if suffix else original_path.name
    prefixed_part_number = f"OPL{part_number}" if part_number else "OPL"
    filename_stem = "_".join(part for part in (prefixed_part_number, original_stem, "OpenPartsLibrary", "www.alsado.de") if part)
    return f"{filename_stem}{suffix}"


def branded_library_filename(filename):
    """Build the public download name for library-generated files.

    :param filename: Desired base filename.
    :return: Branded filename.
    :rtype: str
    """

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
    """Persist a download audit event for analytics and admin dashboards.

    :param session: SQLAlchemy session used to write the event.
    :param download_type: Short category such as ``component_cad``.
    :param downloaded_filename: Final filename sent to the browser.
    :param component: Optional component associated with the download.
    :param file: Optional file associated with the download.
    :param quantity: Optional item quantity represented by the download.
    :return: ``None``.
    """

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
