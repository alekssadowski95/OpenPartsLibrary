from flask import Flask
from flask import render_template, redirect, url_for


# Create flask app instance
application = app = Flask(__name__)

# Add secret key
app.config['SECRET_KEY'] = 'afs87fas7bfsa98fbasbas98fh78oizu'

@app.route('/')
def home():
    return redirect(url_for('viewer', filename = 'base-machine-vise.FCStd'))


@app.route('/new')
def home_new():
    return render_template('index.html')

@app.route('/viewer/<filename>')
def viewer(filename):
    return render_template('viewer.html', filename = filename)

@app.route('/cad-viewer/<filename>')
def cad_viewer():
    pass

@app.route('/pdf-viewer/<filename>')
def pdf_viewer():
    pass

@app.route('/spreadsheet-viewer/<filename>')
def spreadsheet_viewer():
    pass

@app.route('/text-viewer/<filename>')
def text_viewer():
    pass

@app.route('/presentation-viewer/<filename>')
def presentation_viewer():
    pass

