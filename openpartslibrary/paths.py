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

    data_dir.mkdir(parents=True, exist_ok=True)
    cad_dir.mkdir(parents=True, exist_ok=True)
    file_dir.mkdir(parents=True, exist_ok=True)

    app.config["APP_PATH"] = str(PACKAGE_DIR)
    app.config["DATA_DIR"] = data_dir
    app.config["CAD_DIR"] = cad_dir
    app.config["FILE_DIR"] = file_dir
    app.config["DB_PATH"] = data_dir / "parts.db"

    return data_dir, cad_dir, file_dir
