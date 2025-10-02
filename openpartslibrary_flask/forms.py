from flask_wtf import FlaskForm
from wtforms.fields import StringField, TextAreaField, SubmitField, FileField, FloatField
from wtforms.validators import DataRequired, Length


class CreatePartForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=1, max=1000)])
    number = StringField('Part number', default='SPN-1000001')
    owner = StringField('Owner', default='Aleksander Sadowski')
    material = StringField('Material')
    lead_time = FloatField('Lead time (d)', default=30)
    unit_price = FloatField('Unit price (€)')
    file = FileField('CAD file')
    submit = SubmitField('Create part')

class CreateSupplierForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=1, max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(min=1, max=1000)])
    street = StringField('Street', validators=[DataRequired(), Length(min=1, max=200)])
    house_number = StringField('House number', validators=[DataRequired(), Length(min=1, max=20)])
    city = StringField('City', validators=[DataRequired(), Length(min=1, max=100)])
    country = StringField('Country', validators=[DataRequired(), Length(min=1, max=100)])
    postal_code = StringField('Postal code', validators=[DataRequired(), Length(min=1, max=20)])
    submit = SubmitField('Create supplier')