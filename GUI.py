from flask import Flask

app = Flask(__name__)

@app.route("/")
@app.route("/login")
def login():
    return "<p>Welcome to RunAssist!</p>"

@app.route("/logrun")
def log_run():
    return "<p>Log a Run!</p>"

@app.route("/viewstats")
def view_stats():
    return "<p>View Statistics!</p>"