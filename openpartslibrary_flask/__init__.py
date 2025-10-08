import os
import uuid

from flask import Flask
from flask import render_template, url_for, send_from_directory, redirect, request, flash, session
from werkzeug.utils import secure_filename

from sqlalchemy import or_

from flask_cors import CORS

from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Part, Supplier, File, Component, ComponentComponent, Material
from openpartslibrary_flask.forms import CreatePartForm, CreateSupplierForm, CreateMaterialForm


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

# Application paths
app.config['APPLICATION_PATH_FREECAD'] = 'C:/Users/Work/Documents/Github/OpenPartsLibrary/apps/FreeCAD_1.0.2-conda-Windows-x86_64-py311/bin/freecad.exe'
app.config['APPLICATION_PATH_LIBREOFFICE'] = None
app.config['APPLICATION_PATH_PREPOMAX'] = None
app.config['APPLICATION_PATH_KICAD'] = None

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


'''
**************
General routes
**************
'''
@app.route('/')
def home():
    return redirect(url_for('parts'))


''' 
***********
Part routes
***********
'''
@app.route('/parts', defaults={'search_query': None})
def parts(search_query):
    search_query = request.args.get("search_query", "")

    like_pattern = f"%{search_query}%"

    parts = pl.session.query(Part).filter(
            or_(
                Part.name.ilike(like_pattern),
                Part.description.ilike(like_pattern)
            )
        ).limit(1000).all()
    
    return render_template('part/part-list.html', parts = parts, len = len, search_query = search_query)

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
    return render_template('part/part-create.html', form = form) 

@app.route('/part_view/<uuid>')
def part_view(uuid):
    part = pl.session.query(Part).filter_by(uuid = uuid).first()
    part_cad_filepath = os.path.abspath(os.path.join(CAD_DIR, part.cad_reference.uuid + '.FCStd'))
    print(part_cad_filepath)
    return render_template('part/part-read.html', part = part, len = len, part_cad_filepath = part_cad_filepath) 

@app.route('/update-part/<uuid>', methods = ['GET', 'POST'])
def update_part(uuid):
    part = pl.session.query(Part).filter_by(uuid = uuid).first()
    form = CreatePartForm()
    if form.validate_on_submit():
        part.name = str(form.name.data)
        part.description = str(form.description.data)
        part.owner = str(form.owner.data)
        part.material = str(form.material.data)
        part.unit_price = str(form.unit_price.data)
        pl.session.commit()
        return redirect(url_for('part_view', uuid = uuid))
    return render_template('part/part-update.html', form = form, part = part) 

@app.route('/delete-part/<uuid>', methods = ['GET', 'POST'])
def archive_part(uuid):
    part = pl.session.query(Part).filter_by(uuid = uuid).first()
    part.is_archived = True
    return redirect(url_for('parts'))


''' 
***************
Supplier routes
***************
'''
@app. route('/suppliers')
def suppliers():
    suppliers = pl.session.query(Supplier).all()
    return render_template('supplier/supplier-list.html', suppliers = suppliers, len = len)

@app.route('/create-supplier', methods = ['GET', 'POST'])
def create_supplier():
    form = CreateSupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
                uuid = str(uuid.uuid4()),
                name = form.name.data,
                description = form.description.data,
                street = form.street.data,
                house_number = form.house_number.data,
                city = str(form.city.data),
                country = str(form.country.data),
                postal_code = str(form.postal_code.data)
        )
        pl.session.add(supplier)
        pl.session.commit()
        return redirect(url_for('suppliers'))
    return render_template('supplier/supplier-create.html', form = form)

@app.route('/update-supplier/<uuid>', methods = ['GET', 'POST'])
def update_supplier(uuid):
    supplier = pl.session.query(Supplier).filter_by(uuid = uuid).first()
    form = CreateSupplierForm(obj=supplier)
    if form.validate_on_submit():
        form.populate_obj(supplier)
        pl.session.commit() 
        return redirect(url_for('suppliers'))
    return render_template('supplier/supplier-update.html', form = form, supplier = supplier)

@app.route('/delete-supplier/<uuid>', methods = ['GET', 'POST'])
def delete_supplier(uuid):
    supplier = pl.session.query(Supplier).filter_by(uuid = uuid).first()
    pl.session.delete(supplier)
    pl.session.commit()
    return redirect(url_for('suppliers'))

@app.route('/supplier/<uuid>')
def supplier_view(uuid):
    supplier = pl.session.query(Supplier).filter_by(uuid = uuid).first()
    return render_template('supplier/supplier-read.html', supplier = supplier, len = len)


'''
************
Material routes
************
'''
@app.route('/materials')
def materials():
    materials = pl.session.query(Material).all()
    return render_template('material/material-list.html', materials = materials) 

@app.route('/materials/create', methods = ['GET', 'POST'])
def material_create():
    form = CreateMaterialForm()
    if form.validate_on_submit():
        material = Material(
                uuid = str(uuid.uuid4()),
                name = form.name.data,
                category = form.category.data,
                density = form.density.data,
                youngs_modulus = form.youngs_modulus.data,
                yield_strength = form.yield_strength.data,
                poisson_ratio = form.poisson_ratio.data,
                ultimate_strength = form.ultimate_strength.data,
                thermal_conductivity = form.thermal_conductivity.data,
                specific_heat = form.specific_heat.data,
                thermal_expansion = form.thermal_expansion.data
        )
        pl.session.add(material)
        pl.session.commit()
        return redirect(url_for('materials'))
    return render_template('material/material-create.html', form = form)

@app.route('/materials/<int:material_id>')
def material_read(material_id):
    material = pl.session.query(Material).get(material_id)
    if not material:
        flash('Material not found.')
        return redirect(url_for('materials'))
    return render_template('material/material-read.html', material = material)

@app.route('/materials/<int:material_id>/update', methods=['GET', 'POST'])
def material_update(material_id):
    material = pl.session.query(Material).get(material_id)
    if not material:
        flash('Material not found.')
        return redirect(url_for('materials'))
    form = CreateMaterialForm(obj=material)
    if form.validate_on_submit():
        material.name = form.name.data
        material.category = form.category.data
        material.density = form.density.data
        material.youngs_modulus = form.youngs_modulus.data
        material.poisson_ratio = form.poisson_ratio.data
        material.yield_strength = form.yield_strength.data
        material.ultimate_strength = form.ultimate_strength.data
        material.thermal_conductivity = form.thermal_conductivity.data
        material.specific_heat = form.specific_heat.data
        material.thermal_expansion = form.thermal_expansion.data
        pl.session.commit()
        flash('Material updated successfully.')
        return redirect(url_for('materials'))
    return render_template('material/material-update.html', form = form)

@app.route('/materials/<int:material_id>/delete', methods = ['POST'])
def material_delete(material_id):
    material = pl.session.query(Material).get(material_id)
    if not material:
        flash('Material not found.')
        return redirect(url_for('materials'))
    pl.session.delete(material)
    pl.session.commit()
    flash('Material deleted successfully.')
    return redirect(url_for('materials'))

@app.route('/materials/<int:material_id>/archivate', methods = ['POST'])
def material_archivate(material_id):
    material = pl.session.query(Material).get(material_id)
    if not material:
        flash('Material not found.')
        return redirect(url_for('materials'))
    material.is_archived = True
    pl.session.commit()
    flash('Material archivate successfully.')
    return redirect(url_for('materials'))

#Sample data
def add_sample_material():
    if not pl.session.query(Material).filter_by(name="Steel AISI 1020").first():
        material = Material(
            uuid=str(uuid.uuid4()),
            name="Steel AISI 1020",
            density=7.85,  # Convert 7850 kg/m³ to 7.85 g/cm³
            elastic_modulus=2.1e5,  # Convert 2.1e11 Pa to 2.1e5 MPa (or 210 GPa)
            poisson_ratio=0.29,
            yield_strength=350,  # 3.5e8 Pa to 350 MPa
            tensile_strength=420, # 4.2e8 Pa to 420 MPa
            thermal_conductivity=51,
            specific_heat_capacity=486,
            thermal_expansion=1.2e-5
        )
        pl.session.add(material)
        pl.session.commit()
add_sample_material()

        
''' 
***********
File routes
***********
'''
@app.route('/create-file', methods = ['GET', 'POST'])
def create_file():
    return redirect(url_for('parts'))


''' 
***********
Viewer routes
***********
'''
@app.route('/viewer/<filename>')
def viewer(filename):
    filepath = url_for('static', filename=f'data/cad/{filename}')
    print(f"Serving file to viewer : {filepath}")
    return render_template('viewer.html', filepath = filepath)

@app.route('/static/cad/<filename>')
def serve_model_file(filename):
    return send_from_directory(CAD_DIR, filename)


''' 
**********************************
Desktop application startup routes
**********************************
'''
@app.route('/run-freecad-gui/<filepath>')
def run_freecad_gui(filepath):
    os.system('start ' + app.config['APPLICATION_PATH_FREECAD'] + ' ' + filepath)
    return ('', 204)

@app.route('/run-libreoffice-gui/<filepath>')
def run_libreoffice_gui(filepath):
    return ('', 204)

@app.route('/run-prepomax-gui/<filepath>')
def run_prepomax_gui(filepath):
    return ('', 204)

@app.route('/run-kicad-gui/<filepath>')
def run_kicad_gui(filepath):
    return ('', 204)


''' 
***********
Test routes
***********
'''
@app.route('/test-main-view')
def test_main_view():
    return render_template('template-main-view.html')

@app.route('/test-main-view-row')
def test_main_view_row():
    return render_template('template-main-view-row.html')

@app.route('/test-main-view-row-list')
def test_main_view_row_list():
    return render_template('template-main-view-row-list.html', len = len)

@app.route('/database')
def print_database():
    # Get all the items from the database
    components_components = pl.session.query(ComponentComponent).all()
    components = pl.session.query(Component).all()
    parts = pl.session.query(Part).all()
    suppliers = pl.session.query(Supplier).all()
    files = pl.session.query(File).all()
    return render_template('print-database.html', components_components = components_components, components = components, parts = parts, suppliers = suppliers, files = files)