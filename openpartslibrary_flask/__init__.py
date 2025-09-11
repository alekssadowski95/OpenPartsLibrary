import os
import uuid

from flask import Flask
from flask import render_template, url_for

from flask_cors import CORS

from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Part, Supplier, File, Component, ComponentComponent


# Create the flask app instance
app = Flask(__name__)

CORS(app)

# Define the path for the app
app.config['APP_PATH'] = os.path.dirname(os.path.abspath(__file__))

# Add secret key
app.config['SECRET_KEY'] = 'afs87fas7bfsa98fbasbas98fh78oizu'

# Initialize the parts library
db_path = os.path.join(app.static_folder, 'parts.db')
pl = PartsLibrary(db_path = db_path)


''' Routes
'''
@app.route('/')
def home():
    # Clear the parts library
    pl.delete_all()
    pl.add_sample_data()
    return render_template('base.html')

@app.route('/all-parts')
def all_parts():
    parts = pl.session.query(Part).all()
    return render_template('all-parts.html', parts = parts)

@app.route('/viewer/<filename>')
def viewer(filename):
    filename = 'M6x12-Screw.FCStd'
    return render_template('viewer.html', filepath = url_for('static', filename='sample/' + filename))

@app.route('/database')
def database():
    # Get all the items from the database
    components_components = pl.session.query(ComponentComponent).all()
    components = pl.session.query(Component).all()
    parts = pl.session.query(Part).all()
    suppliers = pl.session.query(Supplier).all()
    files = pl.session.query(File).all()
    return render_template('home.html', components_components = components_components, components = components, parts = parts, suppliers = suppliers, files = files)