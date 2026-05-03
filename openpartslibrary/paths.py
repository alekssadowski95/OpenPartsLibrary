import os
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parent
STATIC_DIR = PACKAGE_DIR / "static"
SAMPLE_DIR = PACKAGE_DIR / "sample"


def configure_paths(app):
    data_dir = Path(
        os.environ.get(
            "OPENPARTSLIBRARY_DATA_DIR",
            Path(app.instance_path) / "data",
        )
    ).expanduser().resolve()
    cad_dir = data_dir / "cad"
    file_dir = data_dir / "files"
    mesh_dir = data_dir / "mesh"
    thumbnail_dir = data_dir / "thumbnails"

    data_dir.mkdir(parents=True, exist_ok=True)
    cad_dir.mkdir(parents=True, exist_ok=True)
    file_dir.mkdir(parents=True, exist_ok=True)
    mesh_dir.mkdir(parents=True, exist_ok=True)
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    app.config["APP_PATH"] = str(PACKAGE_DIR)
    app.config["DATA_DIR"] = data_dir
    app.config["CAD_DIR"] = cad_dir
    app.config["FILE_DIR"] = file_dir
    app.config["MESH_DIR"] = mesh_dir
    app.config["THUMBNAIL_DIR"] = thumbnail_dir
    app.config["DB_PATH"] = data_dir / "parts.db"
    app.config["FREECAD_3MF_EXPORT_COMMAND"] = os.environ.get("FREECAD_3MF_EXPORT_COMMAND", "")
    app.config["BLENDER_THUMBNAIL_COMMAND"] = os.environ.get("BLENDER_THUMBNAIL_COMMAND", "")

    return data_dir, cad_dir, file_dir
