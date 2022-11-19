import os
from ast import Assign
from multiprocessing.util import ForkAwareThreadLock
from unittest.mock import NonCallableMagicMock
import db
from flask import Flask, request
import json



app = Flask(__name__)
db_filename = "cms.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

db.init_app(app)
with app.app_context():
    db.create_all()


def success_response(data, code=200):
    """
    Returns a generic success response
    """
    return json.dumps(data), code


def failure_response(message, code=404):
    """
    Returns a generic failure response
    """
    return json.dumps({"error": message}), code

@app.route("/")
def hello():
    """
    Endpoint for the landing page
    """
    return "Hello"









if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)