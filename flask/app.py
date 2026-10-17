from flask import Flask
from flask import request
from flask import session

app = Flask(__name__)

@app.route("/connection")
def hello():
    return "Hello, World"