import os
from ast import Assign
from multiprocessing.util import ForkAwareThreadLock
from unittest.mock import NonCallableMagicMock
from db import db, Profile, Asset, Job, Rating
from flask import Flask, request
import json



app = Flask(__name__)
db_filename = "side_quest.db"

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

@app.route("/api/profile/")
def get_profiles():
    """
    Endpoint for the getting all Profiles
    """
    profile = [profile.serialize() for profile in Profile.query.all()]
    return success_response({"profile": profile})

@app.route("/api/profile/", methods = ["POST"])
def create_profile():
    """
    Endpoint for creating a profile
    """
    body = json.loads(request.data)
    first = body.get("first")
    last = body.get("last")
    email = body.get("email")
    phone_number = body.get("phone_number")
    if first is None or last is None or email is None or phone_number is None:
        return failure_response("Missing first name, last name, email, or phone number", 400)
    profile = Profile(first = first, last = last, email = email, phone_number = phone_number)
    db.session.add(profile)
    db.session.commit()
    return success_response(profile.serialize(), 201)

@app.route("/api/profile/<int:profile_id>/", methods = ["POST"])
def update_profile(profile_id):
    """
    Endpoint for updating a profile
    """
    profile = Profile.query.filter_by(id = profile_id).first()
    body = json.loads(request.data)
    first = body.get("first")
    last = body.get("last")
    email = body.get("email")
    phone_number = body.get("phone_number")
    if first is None or last is None or email is None or phone_number is None:
        return failure_response("Missing first name, last name, email, or phone number", 400)
    profile.first = first 
    profile.last = last 
    profile.email = email 
    profile.phone_number = phone_number 
    db.session.commit()
    return success_response(profile.serialize(), 201)

@app.route("/api/profile/<int:profile_id>/")
def get_profile(profile_id):
    """
    Endpoint for getting a profile by id
    """
    profile = Profile.query.filter_by(id = profile_id).first()
    if profile is None:
        return failure_response("Profile not found!")
    return success_response(profile.serialize())

@app.route("/api/profile/<int:profile_id>/", methods=["DELETE"])
def delete_profile(profile_id):
    """
    Endpoint for deleting a profile by id
    """
    profile = Profile.query.filter_by(id = profile_id).first()
    if profile is None:
        return failure_response("Profile not found!")
    db.session.delete(profile)
    db.session.commit()
    return success_response(profile.serialize())
    

#-----------------IMAGES--------------------------------------------

@app.route("/api/upload/", methods=["POST"])
def upload():
    """
    Endpoint for uploading an image to AWS given its base64 form,
    then storing/returning the URL of that image
    """
    body = json.loads(request.data)
    image_data = body.get("image_data")
    if image_data is None:
        return failure_response("No base64 image found")
    
    asset = Asset(image_data = image_data)
    db.session.add(asset)
    db.session.commit()
    return success_response(asset.serialize(), 201)

#-----------------JOBS--------------------------------------------

@app.route("/api/job/")
def get_jobs():
    """
    Endpoint for getting all jobs
    """
    jobs = [job.serialize() for job in Job.query.all()]
    return success_response({"jobs": jobs})

@app.route("/api/job/", methods=["POST"])
def create_job():
    """
    Endpoint for creating a job
    """
    body = json.loads(request.data)
    title = body.get("title")
    description = body.get("description")
    location = body.get("location")
    date_activity = body.get("date_activity")
    duration = body.get("duration")
    reward = body.get("reward")
    if title is None or description is None or  location is None or  date_activity is None or duration is None or reward is None:
        return failure_response("Missing one of the required fields", 400)
    job = Job(title = title, description = description, location = location, date_activity =date_activity, duration=duration, reward=reward)
    db.session.add(job)
    db.session.commit()
    return success_response(job.serialize(), 201)

@app.route("/api/job/<int:job_id>/", methods = ["POST"])
def update_job(job_id):
    """
    Endpoint for updating a job
    """
    job = Job.query.filter_by(id = job_id).first()
    body = json.loads(request.data)
    title = body.get("title")
    description = body.get("description")
    location = body.get("location")
    date_activity = body.get("date_activity")
    duration = body.get("duration")
    reward = body.get("reward")
    if title is None or description is None or  location is None or  date_activity is None or duration is None or reward is None:
        return failure_response("Missing one of the required fields", 400)
    job.title = title 
    job.description = description 
    job.location = location 
    job.date_activity = date_activity 
    job.duration = duration 
    job.reward = reward 
    db.session.commit()
    return success_response(job.serialize(), 201)

@app.route("/api/job/<int:job_id>/")
def get_job(job_id):
    """
    Endpoint for getting a job by id
    """
    job = Job.query.filter_by(id = job_id).first()
    if job is None:
        return failure_response("Job not found!")
    return success_response(job.serialize())

@app.route("/api/job/<int:job_id>/", methods=["DELETE"])
def delete_job(job_id):
    """
    Endpoint for deleting a job by id
    """
    job = Job.query.filter_by(id = job_id).first()
    if job is None:
        return failure_response("Job not found!")
    db.session.delete(job)
    db.session.commit()
    return success_response(job.serialize())










if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)