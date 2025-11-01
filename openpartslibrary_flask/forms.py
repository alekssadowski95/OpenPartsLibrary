from flask_wtf import FlaskForm
from wtforms.fields import StringField, TextAreaField, SubmitField, FileField, FloatField, PasswordField
from wtforms.validators import DataRequired, Length, Email, EqualTo


class CreateComponentForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=1, max=1000)])
    number = StringField('Component number', default='SPN-1000001')
    owner = StringField('Owner', default='Max Mustermann')
    unit_price = FloatField('Unit price (€)', default='0.00')
    cad_file = FileField('CAD file')
    submit = SubmitField('Create component')

class CreateSupplierForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=1, max=1000)])
    street = StringField('Street', validators=[DataRequired(), Length(min=1, max=200)])
    house_number = StringField('House number', validators=[DataRequired(), Length(min=1, max=20)])
    city = StringField('City', validators=[DataRequired(), Length(min=1, max=100)])
    country = StringField('Country', validators=[DataRequired(), Length(min=1, max=100)])
    postal_code = StringField('Postal code', validators=[DataRequired(), Length(min=1, max=20)])
    submit = SubmitField('Create supplier')

class CreateMaterialForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=1, max=1000)])
    category = StringField('Category', validators=[DataRequired(), Length(min=1, max=100)])
    density = FloatField('Density (g/cm³)', validators=[DataRequired()])
    youngs_modulus = FloatField("Young's modulus (GPa)", validators=[DataRequired()])
    yield_strength = FloatField('Yield strength (MPa)', validators=[DataRequired()])
    poisson_ratio = FloatField("Poisson's ratio", validators=[DataRequired()])
    ultimate_strength = FloatField('Ultimate strength (MPa)', validators=[DataRequired()])
    thermal_conductivity = FloatField('Thermal conductivity (W/mK)', validators=[DataRequired()])
    specific_heat = FloatField('Specific heat (J/gK)', validators=[DataRequired()])
    thermal_expansion = FloatField('Thermal expansion (1/K)', validators=[DataRequired()])
    submit = SubmitField('Create material')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class CreateFileForm(FlaskForm):
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=1, max=1000)])
    file = FileField('Upload file', validators=[DataRequired()])
  
 