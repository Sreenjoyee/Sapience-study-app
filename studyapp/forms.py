from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField , SubmitField, BooleanField, TextAreaField
from wtforms.validators import Length, DataRequired, Email, EqualTo, ValidationError
from studyapp.models import User


class RegistrationForm(FlaskForm):
    username=StringField('USERNAME',validators=[DataRequired(), Length(min=2,max=20)])
    email=StringField('EMAIL', validators=[DataRequired(),Email()])
    password=PasswordField('PASSWORD', validators=[DataRequired()])
    confirm_password=PasswordField('CONFIRM PASSWORD', validators=[DataRequired(), EqualTo('password')])

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('This username is already taken')
        
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('This email already has an account')

class LoginForm(FlaskForm):
    email=StringField('EMAIL', validators=[DataRequired(),Email()])
    password=PasswordField('PASSWORD', validators=[DataRequired()])
    remember=BooleanField('REMEMBER ME')