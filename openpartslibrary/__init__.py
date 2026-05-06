from datetime import timedelta

from flask import Flask
from flask_cors import CORS

from openpartslibrary.admin import setup_admin
from openpartslibrary.boms import ensure_part_boms
from openpartslibrary.db import PartsLibrary
from openpartslibrary.i18n import init_i18n
from openpartslibrary.models import Component, ComponentComponent, DownloadEvent, File, Material, Supplier
from openpartslibrary.paths import configure_paths
from openpartslibrary.routes import register_routes
from openpartslibrary.startup import bootstrap_sample_data, migrate_legacy_database_schema


app = Flask(__name__, instance_relative_config=True)
app.config["SECRET_KEY"] = "afs87fas7bfsa98fbasbas98fh78oizu"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=360)
CORS(app)
babel = init_i18n(app)

data_dir, cad_dir, file_dir = configure_paths(app)
migrate_legacy_database_schema(app.config["DB_PATH"])

pl = PartsLibrary(db_path=app.config["DB_PATH"], data_dir_path=data_dir)
bootstrap_sample_data(pl)
ensure_part_boms(pl.session)

admin = setup_admin(app, pl.session)


@app.context_processor
def inject_admin():
    return {"admin_available": admin is not None and not isinstance(admin, dict)}


register_routes(app, pl)
