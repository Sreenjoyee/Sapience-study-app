from flask import render_template,flash,redirect, request,abort,url_for
from flask_login import login_user,current_user, logout_user, login_required
from studyapp import app,db,bcrypt
from studyapp.forms import RegistrationForm,LoginForm,TaskForm
from studyapp.models import User,ToDo,Resource,Schedule


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


@app.route("/todo/<string:username>")
@login_required
def to_do_list(username):
    if username != current_user.username:
        flash("You are not authorized to view this page.",'info')
        return redirect(url_for("home"))  

    user = User.query.filter_by(username=username).first_or_404()
    todo_task = ToDo.query.filter_by(user=user, is_done=False).all()
    return render_template('to_do_list.html', title='To Do List', tasks=todo_task)

@app.route("/todo/new", methods=["GET", "POST"])
@login_required
def new_task(): 
    form=TaskForm()
    if form.validate_on_submit():
        task=ToDo(task=form.task.data,user = current_user)
        db.session.add(task)
        db.session.commit()
        flash("Task added successfully!", 'success')
        return redirect(url_for('to_do_list', username=current_user.username))
    return render_template('create_new_task.html',title='New Task',form=form)

@app.route('/todo/<int:task_id>')
@login_required
def task(task_id):
    todo_task=ToDo.query.get_or_404(task_id)
    if todo_task.user != current_user:
        abort(403)
    return render_template('task.html',title='Task',task=todo_task)

@app.route('/todo/<int:task_id>/update',methods=['GET','POST'])
@login_required
def update_task(task_id):
    todo_task=ToDo.query.get_or_404(task_id)
    if todo_task.user != current_user:
        abort(403)

    form=TaskForm()
    if form.validate_on_submit():
        todo_task.task = form.task.data
        db.session.commit()
        flash("Task updated successfully!", 'success')
        return redirect(url_for('to_do_list', username=current_user.username))
    
    elif request.method == 'GET':
        form.task.data=todo_task.task

    return render_template('create_new_task.html',title='Update Task', form =form, p='Update Task')

@app.route('/todo/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    todo_task=ToDo.query.get_or_404(task_id)
    if todo_task.user != current_user:
        abort(403)

    db.session.delete(todo_task)
    db.session.commit()
    flash('The task has been deleted!', 'success')
    return redirect(url_for('to_do_list', username=current_user.username))

@app.route('/todo/<int:task_id>/complete', methods=['POST'])
@login_required
def mark_done(task_id):
    task = ToDo.query.get_or_404(task_id)
    if task.user != current_user:
        abort(403)

    task.is_done = True
    db.session.commit()
    flash("Task marked as done!", "success")
    return redirect(url_for('to_do_list', username=current_user.username))


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
