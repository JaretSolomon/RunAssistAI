from flask import Flask , render_template

app = Flask(__name__)

@app.route("/")
@app.route("/home")
def home():
    return render_template('home.html')

@app.route("/logrun")
def log_run():
    return render_template('logrun.html')

@app.route("/viewstats")
def view_stats():
    return render_template('viewstats.html')