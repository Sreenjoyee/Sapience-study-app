from flask import Flask,render_template

app = Flask(__name__)

@app.route("/")
@app.route("/home")
def home():
    return render_template('home_page.html')

@app.route("/todo")
def to_do_list():
    return render_template('to_do_list.html')

@app.route("/resources")
def resources():
    return render_template('resources.html')

@app.route("/pomodromo")
def pomodromo():
    return render_template('pomodromo.html')

@app.route("/calendar")
def calendar():
    return render_template('calendar.html')


if __name__=='__main__':
    app.run(debug=True)
