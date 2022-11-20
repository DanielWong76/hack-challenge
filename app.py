import os
from ast import Assign
from multiprocessing.util import ForkAwareThreadLock
from unittest.mock import NonCallableMagicMock
import db
from flask import Flask, request
import json
import users_dao
import datetime



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

def extract_token(request):
    """
    Helper function that extracts the token from the header of a request
    """
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return False, failure_response("Missing Authorization header.", 400)

    #Header looks like Authorization: Bearer fkafpkakfpow
    bearer_token = auth_header.replace("Bearer ", "").strip()
    if bearer_token is None or not bearer_token:
        return False, failure_response("Invalid authorization header", 400)

    return True, bearer_token

@app.route("/")
def hello_world():
    """
    Endpoint for printing Hello World!
    """
    return "Hello World!"


@app.route("/register/", methods=["POST"])
def register_account():
    """
    Endpoint for registering a new user
    """
    return "Hello"









if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)