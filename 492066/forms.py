from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, FloatField, SelectField, SubmitField, DateField
from wtforms.validators import DataRequired, Length, NumberRange, EqualTo, Optional

class TransactieForm(FlaskForm):
    type = SelectField('Type', choices=[('inkomst', 'Inkomst'), ('uitgave', 'Uitgave')], validators=[DataRequired()])
    omschrijving = StringField('Omschrijving', validators=[DataRequired(), Length(min=1, max=200)])
    bedrag = FloatField('Bedrag', validators=[DataRequired(), NumberRange(min=0)])
    categorie_id = SelectField('Categorie', coerce=int, validators=[Optional()])
    spaarpotje_id = SelectField('Spaarpotje', coerce=int, validators=[Optional()])
    submit = SubmitField('Toevoegen')

class LoginForm(FlaskForm):
    username = StringField('Gebruikersnaam', validators=[DataRequired(), Length(min=1, max=80)])
    password = PasswordField('Wachtwoord', validators=[DataRequired()])
    submit = SubmitField('Inloggen')

class RegisterForm(FlaskForm):
    username = StringField('Gebruikersnaam', validators=[DataRequired(), Length(min=4, max=80)])
    password = PasswordField('Wachtwoord', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Bevestig wachtwoord', validators=[
        DataRequired(),
        EqualTo('password', message='Wachtwoorden komen niet overeen')])
    submit = SubmitField('Registreren')

class CategorieForm(FlaskForm):
    naam = StringField('Naam', validators=[DataRequired(), Length(min=1, max=50)])
    submit = SubmitField('Toevoegen')

class BudgetForm(FlaskForm):
    bedrag = FloatField('Bedrag', validators=[DataRequired(), NumberRange(min=0)])
    categorie_id = SelectField('Categorie', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Toevoegen')

class SpaarpotjeForm(FlaskForm):
    naam = StringField('Naam', validators=[DataRequired(), Length(min=1, max=100)])
    doelbedrag = FloatField('Doelbedrag', validators=[DataRequired(), NumberRange(min=0)])
    submit = SubmitField('Toevoegen')

class SpaarpotjeGeldForm(FlaskForm):
    bedrag = FloatField('Bedrag', validators=[DataRequired(), NumberRange(min=0)])
    type = SelectField('Type', choices=[('toevoegen', 'Toevoegen'), ('afhalen', 'Afhalen')], validators=[DataRequired()])
    submit = SubmitField('Uitvoeren') 