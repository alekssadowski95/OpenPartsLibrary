import os
import uuid

from flask import Flask
from flask import render_template, url_for, send_from_directory, redirect, request, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from .settings import load_settings, save_settings

from sqlalchemy import or_

from flask_cors import CORS

from openpartslibrary.db import PartsLibrary
from openpartslibrary.models import Supplier, File, Component, ComponentComponent, Material, User
from openpartslibrary_flask.forms import CreateComponentForm, CreateSupplierForm, CreateMaterialForm, LoginForm, RegistrationForm, CreateFileForm


# Setup directories
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
DATA_DIR = os.path.join(STATIC_DIR, 'data')
CAD_DIR = os.path.join(DATA_DIR,'cad')
FILE_DIR = os.path.join(DATA_DIR,'files')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CAD_DIR, exist_ok=True)
os.makedirs(FILE_DIR, exist_ok=True)
 
# Create the flask app instance
app = Flask(__name__)

# Enable cross origin resource sharing
CORS(app)

# Define the path for the app
app.config['APP_PATH'] = os.path.dirname(os.path.abspath(__file__))

# Add secret key
app.config['SECRET_KEY'] = 'afs87fas7bfsa98fbasbas98fh78oizu'

# Application paths
# initialize

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
#copy_sample_files()

# Clear the parts library
pl.delete_all()
pl.import_from_spreadsheet(os.path.join(pl.sample_data_dir_path, 'components.ods'))

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # redirect unauthorized users

@app.context_processor
def inject_user():
    return dict(user=current_user)

@login_manager.user_loader
def load_user(user_id):
    return pl.session.query(User).filter_by(id=int(user_id)).first()


'''
**************
General routes
**************
'''
@app.route('/')
def home():
    return redirect(url_for('components'))

'''
**************
User routes
**************
'''
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pw = generate_password_hash(form.password.data)
        user = User(
            username = form.username.data, 
            email = form.email.data, 
            password = hashed_pw
        )
        pl.session.add(user)
        pl.session.commit()
        return redirect(url_for('login'))
    return render_template('user/user-register.html', form = form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('profile'))
    form = LoginForm()
    if form.validate_on_submit():
        user = pl.session.query(User).filter_by(email=form.email.data).first()
        if user and check_password_hash(user.password, form.password.data):
            login_user(user)
            print("Authenticated after login", current_user.is_authenticated)
            return redirect(url_for('profile'))
        else:
            flash('Invalid email or password', 'danger')
    return render_template('user/user-login.html', form = form)

@app.route('/profile')
@login_required
def profile():
    return render_template('user/user-profile.html', user = current_user)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

''' 
***********
Component routes
***********
'''
@app.route('/components', defaults={'search_query': None})
def components(search_query):
    search_query = request.args.get("search_query", "")

    like_pattern = f"%{search_query}%"

    components = pl.session.query(Component).filter(
            or_(
                Component.name.ilike(like_pattern),
                Component.description.ilike(like_pattern)
            )
        ).limit(1000).all()
    
    return render_template('component/component-list.html', components = components, len = len, search_query = search_query, user = current_user)

@app.route('/component/create', methods = ['GET', 'POST'])
def component_create():
    form = CreateComponentForm()
    if form.validate_on_submit():
        # check if the post request has the file component
        if "cad_file" not in request.files:
            return "No file component", 400

        cad_file = request.files["cad_file"]

        if cad_file.filename == "":
            return "No selected cad file", 400

        file_uuid = str(uuid.uuid4())

        # Sanitize filename and save
        file_name = file_uuid + '.FCStd'
        cad_file.save(os.path.join(CAD_DIR, file_name))
        
        # Create a new file
        cad_file = File(uuid = file_uuid, name = file_name, description = 'This is a CAD file.')

        # Create a new component
        component = Component(
                uuid = str(uuid.uuid4()),
                number = str(form.number.data),
                name = str(form.name.data),
                description = str(form.description.data),
                revision = "1",
                lifecycle_state = "In Work",
                owner = str(form.owner.data),
                manufacturer_number = 'MFN-100001',
                unit_price = str(form.unit_price.data),
                currency = 'EUR',
                cad_file = cad_file
        )
        pl.session.add(component)
        pl.session.commit()
        return redirect(url_for('components'))
    return render_template('component/component-create.html', form = form) 

@app.route('/component_view/<uuid>')
def component_view(uuid):
    component = pl.session.query(Component).filter_by(uuid = uuid).first()
    if component is None:
        return f"Component not found with UUID: {uuid}", 404
    component_cad_filepath = os.path.abspath(os.path.join(CAD_DIR, component.cad_file.uuid + '.FCStd'))
    files = component.files if component else []
    used_in_files = []
    return render_template('component/component-read.html', component = component, len = len, component_cad_filepath = component_cad_filepath, files = files, used_in_files = used_in_files) 

@app.route('/update-component/<uuid>', methods = ['GET', 'POST'])
def component_update(uuid):
    component = pl.session.query(Component).filter_by(uuid = uuid).first()
    form = CreateComponentForm()
    if form.validate_on_submit():
        component.name = str(form.name.data)
        component.description = str(form.description.data)
        component.owner = str(form.owner.data)
        component.material = str(form.material.data)
        component.unit_price = str(form.unit_price.data)
        pl.session.commit()
        return redirect(url_for('component_view', uuid = uuid))
    return render_template('component/component-update.html', form = form, component = component) 

@app.route('/component/archivate/<uuid>', methods = ['GET', 'POST'])
def component_archivate(uuid):
    component = pl.session.query(Component).filter_by(uuid = uuid).first()
    component.is_archived = True
    return redirect(url_for('components'))

''' 
***************
Supplier routes
***************
'''
@app. route('/suppliers')
def suppliers():
    suppliers = pl.session.query(Supplier).all()
    return render_template('supplier/supplier-list.html', suppliers = suppliers, len = len)

@app.route('/supplier/create', methods = ['GET', 'POST'])
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

@app.route('/supplier/update/<uuid>', methods = ['GET', 'POST'])
def update_supplier(uuid):
    supplier = pl.session.query(Supplier).filter_by(uuid = uuid).first()
    form = CreateSupplierForm(obj=supplier)
    if form.validate_on_submit():
        form.populate_obj(supplier)
        pl.session.commit() 
        return redirect(url_for('suppliers'))
    return render_template('supplier/supplier-update.html', form = form, supplier = supplier)

@app.route('/supplier/delete/<uuid>', methods = ['GET', 'POST'])
def supplier_delete(uuid):
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

@app.route('/materials/<uuid>')
def material_read(uuid):
    material = pl.session.query(Material).filter_by(uuid = uuid).first()
    if not material:
        return redirect(url_for('materials'))
    return render_template('material/material-read.html', material = material)

@app.route('/materials/<uuid>/update', methods=['GET', 'POST'])
def material_update(uuid):
    material = pl.session.query(Material).filter_by(uuid = uuid).first()
    if not material:
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
        return redirect(url_for('materials'))
    return render_template('material/material-update.html', form = form)

@app.route('/materials/<uuid>/delete', methods = ['POST'])
def material_delete(uuid):
    material = pl.session.query(Material).filter_by(uuid = uuid).first()
    if not material:
        return redirect(url_for('materials'))
    pl.session.delete(material)
    pl.session.commit()
    return redirect(url_for('materials'))

@app.route('/materials/<uuid>/archivate', methods = ['POST'])
def material_archivate(uuid):
    material = pl.session.query(Material).filter_by(uuid = uuid).first()
    if not material:
        return redirect(url_for('materials'))
    material.is_archived = True
    pl.session.commit()
    return redirect(url_for('materials'))
        
''' 
***********
File routes
***********
'''
@app.route('/file/create/<component_uuid>', methods = ['GET', 'POST'])
def file_create(component_uuid):
    form = CreateFileForm()
    component = pl.session.query(Component).filter_by(uuid = component_uuid).first()
    if component is None:
        return f"Component not found with UUID: {component_uuid}", 404
    if form.validate_on_submit():
        uploaded_file = request.files['file']
        if uploaded_file.filename == '':
            return "No selected file", 400
        file_uuid = str(uuid.uuid4())
        file_name = secure_filename(uploaded_file.filename)
        stored_file_name = file_uuid + os.path.splitext(file_name)[1]
        upload_path = os.path.join(FILE_DIR, stored_file_name)
        uploaded_file.save(upload_path)
        file = File(uuid = file_uuid, name = file_name, description = form.description.data)
        pl.session.add(file)
        component.files.append(file)
        pl.session.commit()
        return redirect(url_for('component_view', uuid = component_uuid))
    return render_template('file/file-create.html', form = form, component = component)

@app.route('/file/read/<file_uuid>')
def read_file(file_uuid):
    file = pl.session.query(File).filter_by(uuid = file_uuid).first()
    if file is None:
        return f"File not found with UUID: {file_uuid}", 404
    return render_template('file/file-read.html', file = file)

@app.route('/file/update/<file_uuid>', methods = ['GET', 'POST'])
def update_file(file_uuid):
    file = pl.session.query(File).filter_by(uuid = file_uuid).first()
    if file is None:
        return f"File not found with UUID: {file_uuid}", 404
    form = CreateFileForm(obj = file)
    if form.validate_on_submit():
        uploaded_file = request.files['file']
        if uploaded_file and uploaded_file.filename != '':
            file_name = secure_filename(uploaded_file.filename)
            stored_file_name = file.uuid + os.path.splitext(file_name)[1]
            upload_path = os.path.join(FILE_DIR, stored_file_name)
            uploaded_file.save(upload_path)
            file.name = file_name
        file.description = form.description.data
        pl.session.commit()
        component = file.components[0] if file.parts else None
        if component:
            return redirect(url_for('part_view', uuid = component.uuid))
        else:
            return "File updated, but no associated part found.", 200
    return render_template('file/file-update.html', form = form, file = file)

@app.route('/file/delete/<file_uuid>', methods = ['GET', 'POST'])
def delete_file(file_uuid):
    file = pl.session.query(File).filter_by(uuid = file_uuid).first()
    if file is None:
        return f"File not found with UUID: {file_uuid}", 404
    for part in file.parts:
        part.files.remove(file)
    pl.session.delete(file)
    pl.session.commit()
    return redirect(url_for('parts'))

@app.route('/file-list')
def file_list():
    files = pl.session.query(File).all()
    return render_template('file/file-list.html', files = files)

'''
*************
Settings routes
*************
'''
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    settings = load_settings()
    if request.method == 'POST':
        settings['executables']['FreeCAD_GUI'] = request.form.get('FreeCAD_GUI', '')
        settings['executables']['FreeCAD_CMD'] = request.form.get('FreeCAD_CMD', '')
        settings['executables']['PrePoMax'] = request.form.get('PrePoMax', '')
        settings['executables']['LibreOffice_Writer'] = request.form.get('LibreOffice_Writer', '')
        settings['executables']['LibreOffice_Calc'] = request.form.get('LibreOffice_Calc', '')
        settings['executables']['LibreOffice_Impress'] = request.form.get('LibreOffice_Impress', '')
        save_settings(settings)
        return redirect(url_for('settings'))
    return render_template('settings/settings.html', settings = settings)
        
''' 
***********
Viewer routes
***********
'''
@app.route('/viewer/<filename>')
def viewer(filename):
    filepath = url_for('static', filename=f'data/cad/{filename}')
    print(f"Serving file to viewer : {filepath}")
    return render_template('viewer/viewer.html', filepath = filepath)

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
    suppliers = pl.session.query(Supplier).all()
    files = pl.session.query(File).all()
    return render_template('debug/print-database.html', components_components = components_components, components = components, suppliers = suppliers, files = files)