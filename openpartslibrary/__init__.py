"""Application factory module for the bundled OpenPartsLibrary Flask app.

The :func:`create_app` function performs runtime setup and exposes :data:`app`
for WSGI or desktop startup scripts.  Documentation builds can import submodules
without creating a database by setting ``OPENPARTSLIBRARY_SKIP_APP_INIT=1``.
"""

import os
from datetime import timedelta

from flask import Flask
from flask_cors import CORS


def create_app():
    """Create and configure the OpenPartsLibrary Flask application.

    :return: Fully configured Flask application.
    :rtype: flask.Flask
    """

    from openpartslibrary.admin import setup_admin
    from openpartslibrary.boms import ensure_part_boms
    from openpartslibrary.db import PartsLibrary
    from openpartslibrary.i18n import init_i18n
    from openpartslibrary.paths import configure_paths
    from openpartslibrary.routes import register_routes
    from openpartslibrary.startup import bootstrap_sample_data, migrate_legacy_database_schema

    flask_app = Flask(__name__, instance_relative_config=True)
    flask_app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "afs87fas7bfsa98fbasbas98fh78oizu")
    flask_app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=360)
    CORS(flask_app)
    init_i18n(flask_app)

    data_dir, _, _ = configure_paths(flask_app)
    migrate_legacy_database_schema(flask_app.config["DB_PATH"])

    parts_library = PartsLibrary(db_path=flask_app.config["DB_PATH"], data_dir_path=data_dir)
    bootstrap_sample_data(parts_library)
    ensure_part_boms(parts_library.session)

    admin = setup_admin(flask_app, parts_library.session)

    @flask_app.context_processor
    def inject_admin():
        """Expose admin availability to Jinja templates.

        :return: Template context with an ``admin_available`` boolean.
        :rtype: dict
        """

        return {"admin_available": admin is not None and not isinstance(admin, dict)}

    register_routes(flask_app, parts_library)
    return flask_app


if os.environ.get("OPENPARTSLIBRARY_SKIP_APP_INIT") == "1":
    app = None
else:
    app = create_app()
