from flask import render_template,flash,redirect, request,abort,url_for
from flask_login import login_user,current_user, logout_user, login_required
from studyapp import app,db,bcrypt
from studyapp.forms import RegistrationForm,LoginForm,TaskForm,ResourceForm,UpdateForm
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
            return redirect(url_for('home'))
        else:
            flash("Login unsuccessful please provide the correct email and password", 'danger')
    return render_template('login.html',title='Login',form=form)

@app.route('/logout')  
def logout():
    logout_user()
    return redirect(url_for('home'))

#ACCOUNT
@app.route('/account',methods=['GET','POST'])  
@login_required
def account():
    form = UpdateForm()
    if form.validate_on_submit():
        current_user.username= form.username.data
        current_user.email=form.email.data
        db.session.commit()
        flash("Your account was updated successfully", 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username 
        form.email.data = current_user.email 
    return render_template('account.html',title='Account', form =form)

#TO DO LIST
@app.route("/todo/<string:username>")
@login_required
def to_do_list(username):
    if username != current_user.username:
        flash("You are not authorized to view this page.",'info')
        return redirect(url_for("home"))  

    todo_task = ToDo.query.filter_by(user=current_user, is_done=False).all()
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


#RESOURCE HUB LINKS
@app.route('/resources/<username>', methods=['GET'])
@login_required
def resources(username):
    if username != current_user.username:
        flash("You are not authorized to view this page.",'info')
        return redirect(url_for("home"))

    search_query = request.args.get('q', '').strip()
    if search_query:
        resources = Resource.query.filter(
            Resource.user == current_user,
            Resource.title.ilike(f"%{search_query}%")
        ).all()
    else:
        resources = Resource.query.filter_by(user=current_user).all()
    
    return render_template('resources.html', resources=resources)

@app.route("/resources/new", methods=["GET", "POST"])
@login_required
def new_link(): 
    form=ResourceForm()
    if form.validate_on_submit():
        resource=Resource(title=form.title.data,link=form.link.data,user = current_user)
        db.session.add(resource)
        db.session.commit()
        flash("Link added successfully!", 'success')
        return redirect(url_for('resources', username=current_user.username))
    return render_template('create_new_link.html',title='New Link',form=form)

@app.route('/resources/<int:link_id>')
@login_required
def view_link(link_id):
    resource=Resource.query.get_or_404(link_id)
    if resource.user != current_user:
        abort(403)
    return render_template('link.html',title='Link',resource=resource)

@app.route('/resources/<int:link_id>/update',methods=['GET','POST'])
@login_required
def update_link(link_id):
    resource=Resource.query.get_or_404(link_id)
    if resource.user != current_user:
        abort(403)

    form=ResourceForm()
    if form.validate_on_submit():
        resource.title = form.title.data
        resource.link = form.link.data
        db.session.commit()
        flash("Link updated successfully!", 'success')
        return redirect(url_for('resources', username=current_user.username))
    
    elif request.method == 'GET':
        form.title.data=resource.title
        form.link.data=resource.link

    return render_template('create_new_link.html',title='Update Link', form =form, p='Update Link')

@app.route('/resources/<int:link_id>/delete', methods=['POST'])
@login_required
def delete_link(link_id):
    resource=Resource.query.get_or_404(link_id)
    if resource.user != current_user:
        abort(403)

    db.session.delete(resource)
    db.session.commit()
    flash('The link has been deleted!', 'success')
    return redirect(url_for('resources', username=current_user.username))

#POMODROMO
@app.route("/pomodromo")
@login_required
def pomodromo():
    return render_template('pomodromo.html',title='Pomodromo')

#CALENDAR
@app.route("/calendar")
@login_required
def calendar():
    return render_template('calendar.html',title='Calendar')

@app.route("/calendar_task")
@login_required
def calendar_task():
    return render_template('calendar_task.html',title='Calendar Task')
