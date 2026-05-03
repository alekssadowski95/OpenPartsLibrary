import os

from openpartslibrary import app

if __name__ == '__main__':
    app.run(
        host=os.environ.get("HOST", "localhost"),
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("FLASK_DEBUG", "1") == "1",
    )
