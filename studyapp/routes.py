from flask import render_template,flash,redirect, request,abort,url_for
from flask_login import login_user,current_user, logout_user, login_required
from studyapp import app,db,bcrypt
from studyapp.forms import RegistrationForm,LoginForm
from studyapp.models import User


@app.route("/")
@app.route("/home")
def home():
    return render_template('home_page.html')

@app.route('/register',methods=['GET','POST']) 
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form=RegistrationForm()
    if form.validate_on_submit():
        hashed_password=bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user=User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash(f'Account created for {form.username.data}!','success')
        return redirect(url_for('login'))
    
    return render_template('register.html',title='Register',form=form) 

@app.route('/login',methods=['GET','POST']) 
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    form=LoginForm()
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page=request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('home'))
        else:
            flash("Login unsuccessful please provide the correct email and password", 'danger')
    return render_template('login.html',title='Login',form=form)

@app.route('/logout')  
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/todo")
@login_required
def to_do_list():
    return render_template('to_do_list.html',title='To Do List')

@app.route("/resources")
@login_required
def resources():
    return render_template('resources.html',title='Resources Link Hub')

@app.route("/pomodromo")
@login_required
def pomodromo():
    return render_template('pomodromo.html',title='Pomodromo')

@app.route("/calendar")
@login_required
def calendar():
    return render_template('calendar.html',title='Calendar')

@app.route("/calendar_task")
@login_required
def calendar_task():
    return render_template('calendar_task.html',title='Calendar Task')
