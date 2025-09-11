import os

from flask import Flask
from flask import render_template

from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Part


# Create the flask app instance
app = Flask(__name__)

# Define the path for the app
app.config['APP_PATH'] = os.path.dirname(os.path.abspath(__file__))

# Add secret key
app.config['SECRET_KEY'] = 'afs87fas7bfsa98fbasbas98fh78oizu'

# Initialize the parts library
db_path = os.path.join(app.static_folder, 'parts.db')
pl = PartsLibrary(db_path = db_path)
pl.delete_all()


''' Routes
'''
@app.route('/')
def index():
    parts = pl.session.query(Part).all()
    return render_template('home.html', parts = parts)


if __name__ == '__main__':
    app.run(host="localhost", port=5000, debug=True)