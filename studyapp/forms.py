from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField , BooleanField, TextAreaField
from wtforms.validators import Length, DataRequired, Email, EqualTo, ValidationError,URL
from studyapp.models import User


class RegistrationForm(FlaskForm):
    username=StringField('USERNAME',validators=[DataRequired(), Length(min=2,max=20)])
    email=StringField('EMAIL', validators=[DataRequired(),Email(), Length(max=320)])
    password=PasswordField('PASSWORD', validators=[DataRequired(), Length(max=60)])
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

class UpdateForm(FlaskForm):
    username=StringField('USERNAME',validators=[DataRequired(), Length(min=2,max=20)])
    email=StringField('EMAIL', validators=[DataRequired(), Email(), Length(max=320)])

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('This username is already taken')
        
    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('This email already has an account')

class TaskForm(FlaskForm):
    task=StringField(validators=[DataRequired(),Length(min=1,max=200)])

class ResourceForm(FlaskForm):
    title=StringField(validators=[DataRequired(),Length(min=1,max=200)])
    link = TextAreaField(validators=[DataRequired(), Length(max=2048), URL()])

class ScheduleForm(FlaskForm):
    notes = TextAreaField(validators=[DataRequired()])

class RequestResetForm(FlaskForm):
    email=StringField('Email', validators=[DataRequired(),Email()])
    
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('This email has no account. You must register first.')

class ResetPasswordForm(FlaskForm):
    password=PasswordField('Password', validators=[DataRequired(), Length(max=60)])
    confirm_password=PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
