import os
import uuid

from flask import Flask
from flask import render_template, url_for, send_from_directory

from flask_cors import CORS

from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Part, Supplier, File, Component, ComponentComponent

STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
CAD_DIR = os.path.join(STATIC_DIR, 'data','cad')
os.makedirs(CAD_DIR, exist_ok=True)

#Function to copy sample files to data directory
# import shutil
#def copy_sample_files():
#    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'openpartslibrary', 'sample'))
 #   print(f"Looking for model files in : {sample_dir}" )
  #  if not os.path.isdir(sample_dir):
   #     print(f"Sample directory does not exist: {sample_dir}")
    #    return
    #for fname in os.listdir(sample_dir):
     #   print(f"Found sample file: {fname}")
      #  if fname.endswith('.FCStd'):
       #     src = os.path.join(sample_dir, fname)
        #    dst = os.path.join(MODELS_DIR, fname)
         #   print(f"Checking if exists: {dst}")
          #  print(f"Is file ? {os.path.isfile(dst)}")
           # if os.path.isfile(src) and not os.path.isfile(dst):
            #    print(f"Copying {src} to {dst}")
             #   shutil.copy(src, dst)
            #else:
             #   print(f"Skipped copying {fname}: already exists or not a file.")

# Create the flask app instance
app = Flask(__name__)

CORS(app)
#copy_sample_files()

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
    return render_template('all-parts.html', parts = parts, len = len)

@app.route('/viewer/<filename>')
def viewer(filename):
    filepath = url_for('static', filename=f'data/cad/{filename}')
    print(f"Serving file to viewer : {filepath}")
    return render_template('viewer.html', filepath = filepath)

#Add route to serve model files
@app.route('/static/cad/<filename>')
def serve_model_file(filename):
    return send_from_directory(CAD_DIR, filename)

@app.route('/database')
def database():
    # Get all the items from the database
    components_components = pl.session.query(ComponentComponent).all()
    components = pl.session.query(Component).all()
    parts = pl.session.query(Part).all()
    suppliers = pl.session.query(Supplier).all()
    files = pl.session.query(File).all()
    return render_template('home.html', components_components = components_components, components = components, parts = parts, suppliers = suppliers, files = files)