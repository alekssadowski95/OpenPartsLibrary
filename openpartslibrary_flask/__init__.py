import os
import uuid

from flask import Flask
from flask import render_template, url_for, send_from_directory, redirect, request
from werkzeug.utils import secure_filename

from flask_cors import CORS

from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Part, Supplier, File, Component, ComponentComponent
from openpartslibrary_flask.forms import CreatePartForm


# Setup directories
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
DATA_DIR = os.path.join(STATIC_DIR, 'data')
CAD_DIR = os.path.join(DATA_DIR,'cad')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CAD_DIR, exist_ok=True)

# Create the flask app instance
app = Flask(__name__)

# Enable cross origin resource sharing
CORS(app)

# Define the path for the app
app.config['APP_PATH'] = os.path.dirname(os.path.abspath(__file__))

# Add secret key
app.config['SECRET_KEY'] = 'afs87fas7bfsa98fbasbas98fh78oizu'

# Initialize the parts library
db_path = os.path.join(app.static_folder, 'data', 'parts.db')
pl = PartsLibrary(db_path = db_path, data_dir_path = DATA_DIR)

# Function to copy sample files to data directory
import shutil
def copy_sample_files():
    sample_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'openpartslibrary', 'sample'))
    print(f"Looking for model files in : {sample_dir}" )
    if not os.path.isdir(sample_dir):
        print(f"Sample directory does not exist: {sample_dir}")
        return
    for fname in os.listdir(sample_dir):
        print(f"Found sample file: {fname}")
        if fname.endswith('.FCStd'):
            src = os.path.join(sample_dir, fname)
            dst = os.path.join(CAD_DIR, fname)
            print(f"Checking if exists: {dst}")
            print(f"Is file ? {os.path.isfile(dst)}")
            if os.path.isfile(src) and not os.path.isfile(dst):
                print(f"Copying {src} to {dst}")
                shutil.copy(src, dst)
            else:
                print(f"Skipped copying {fname}: already exists or not a file.")

# Copy sample files to data dir
copy_sample_files()

# Clear the parts library
pl.delete_all()
pl.add_sample_data()


''' Routes
'''
@app.route('/')
def home():
    return render_template('base.html')

@app.route('/all-parts')
def all_parts():
    parts = pl.session.query(Part).all()
    return render_template('all-parts.html', parts = parts, len = len)

@app.route('/create-part', methods = ['GET', 'POST'])
def create_part():
    form = CreatePartForm()
    if form.validate_on_submit():
        # check if the post request has the file part
        if "file" not in request.files:
            return "No file part", 400

        file = request.files["file"]

        if file.filename == "":
            return "No selected file", 400

        file_uuid = str(uuid.uuid4())

        # Sanitize filename and save
        file_name = file_uuid + '.FCStd'
        file.save(os.path.join(CAD_DIR, file_name))
        
        # Create a new file
        file = File(uuid = file_uuid, name = file_name, description = 'This is a CAD file.')

        part = Part(
                uuid = str(uuid.uuid4()),
                number = str(form.number.data),
                name = str(form.name.data),
                description = str(form.description.data),
                revision = "1",
                lifecycle_state = "In Work",
                owner = str(form.owner.data),
                material = str(form.material.data),
                mass = 0.0,
                dimension_x = 0.0,
                dimension_y = 0.0,
                dimension_z = 0.0,
                quantity = 0,
                attached_documents_reference = 'DOCUMENTS REFERENCE',
                lead_time = 30,
                make_or_buy = 'make',
                manufacturer_number = 'MFN-100001',
                unit_price = str(form.unit_price.data),
                currency = 'EUR',
                cad_reference = file
        )
        pl.session.add(part)
        pl.session.commit()

        supplier = pl.session.query(Supplier).filter_by(id = 1).first()
        supplier.parts.append(part)
        pl.session.commit()

        component = Component(uuid = str(uuid.uuid4()), part = part, name = part.name)
        pl.session.add(component)
        pl.session.commit()
        return redirect(url_for('all_parts'))
    return render_template('create-part.html', form = form) 

@app.route('/search-parts/<search_query>')
def search_parts(search_query):
    return render_template('search-parts.html') 

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