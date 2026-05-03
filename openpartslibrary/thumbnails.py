import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path


THUMBNAIL_SIZE = 512


@dataclass(frozen=True)
class ThumbnailResult:
    status: str
    thumbnail_path: Path | None = None
    mesh_path: Path | None = None
    message: str = ""

    @property
    def ready(self):
        return self.status == "ready" and self.thumbnail_path is not None


def placeholder_thumbnail_svg(label="No preview"):
    safe_label = str(label or "No preview")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{THUMBNAIL_SIZE}" height="{THUMBNAIL_SIZE}" viewBox="0 0 {THUMBNAIL_SIZE} {THUMBNAIL_SIZE}">
  <rect width="100%" height="100%" fill="#f3f5f8"/>
  <path d="M160 190 256 135l96 55v112l-96 55-96-55z" fill="#d9e1ec" stroke="#aebbd0" stroke-width="10" stroke-linejoin="round"/>
  <path d="M160 190 256 246l96-56M256 246v111" fill="none" stroke="#aebbd0" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="256" y="420" text-anchor="middle" font-family="Arial, sans-serif" font-size="28" fill="#6b7280">{safe_label}</text>
</svg>"""


def split_command(command):
    return shlex.split(command, posix=os.name != "nt")


def format_command(command_template, **values):
    formatted = command_template.format(**{key: str(value) for key, value in values.items()})
    return split_command(formatted)


def run_command(command_template, timeout, **values):
    if not command_template:
        return False, "Command is not configured."

    command = format_command(command_template, **values)
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode == 0:
        return True, ""

    output = "\n".join(part for part in (completed.stdout, completed.stderr) if part).strip()
    return False, output or f"Command exited with status {completed.returncode}."


def ensure_3mf_mesh(cad_path, mesh_path, command_template, timeout=120):
    cad_path = Path(cad_path)
    mesh_path = Path(mesh_path)
    if mesh_path.exists() and mesh_path.stat().st_mtime >= cad_path.stat().st_mtime:
        return True, ""

    mesh_path.parent.mkdir(parents=True, exist_ok=True)
    return run_command(
        command_template,
        timeout,
        cad_path=cad_path,
        mesh_path=mesh_path,
    )


def ensure_thumbnail(mesh_path, thumbnail_path, command_template, timeout=120):
    mesh_path = Path(mesh_path)
    thumbnail_path = Path(thumbnail_path)
    if thumbnail_path.exists() and thumbnail_path.stat().st_mtime >= mesh_path.stat().st_mtime:
        return True, ""

    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
    return run_command(
        command_template,
        timeout,
        mesh_path=mesh_path,
        thumbnail_path=thumbnail_path,
        thumbnail_size=THUMBNAIL_SIZE,
    )


def ensure_cad_thumbnail(cad_file_uuid, cad_dir, mesh_dir, thumbnail_dir, freecad_command, blender_command):
    cad_path = Path(cad_dir) / f"{cad_file_uuid}.FCStd"
    mesh_path = Path(mesh_dir) / f"{cad_file_uuid}.3mf"
    thumbnail_path = Path(thumbnail_dir) / f"{cad_file_uuid}.png"

    if thumbnail_path.exists() and (not cad_path.exists() or thumbnail_path.stat().st_mtime >= cad_path.stat().st_mtime):
        return ThumbnailResult("ready", thumbnail_path=thumbnail_path, mesh_path=mesh_path)

    if not cad_path.exists():
        return ThumbnailResult("missing_cad", message="CAD file not found.")

    mesh_ok, mesh_message = ensure_3mf_mesh(cad_path, mesh_path, freecad_command)
    if not mesh_ok:
        return ThumbnailResult("mesh_pending", mesh_path=mesh_path, message=mesh_message)

    thumbnail_ok, thumbnail_message = ensure_thumbnail(mesh_path, thumbnail_path, blender_command)
    if not thumbnail_ok:
        return ThumbnailResult("thumbnail_pending", mesh_path=mesh_path, message=thumbnail_message)

    return ThumbnailResult("ready", thumbnail_path=thumbnail_path, mesh_path=mesh_path)
