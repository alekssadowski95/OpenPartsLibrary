from flask import Flask
from flask_cors import CORS

from openpartslibrary.admin import setup_admin
from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Component, ComponentComponent, DownloadEvent, File, Material, Supplier
from openpartslibrary.paths import configure_paths
from openpartslibrary.routes import register_routes
from openpartslibrary.startup import bootstrap_sample_data, migrate_legacy_database_schema


app = Flask(__name__, instance_relative_config=True)
app.config["SECRET_KEY"] = "afs87fas7bfsa98fbasbas98fh78oizu"
CORS(app)

data_dir, cad_dir, file_dir = configure_paths(app)
migrate_legacy_database_schema(app.config["DB_PATH"])

pl = PartsLibrary(db_path=app.config["DB_PATH"], data_dir_path=data_dir)
bootstrap_sample_data(pl)

admin = setup_admin(app, pl.session)


@app.context_processor
def inject_admin():
    return {"admin_available": admin is not None}


register_routes(app, pl)
