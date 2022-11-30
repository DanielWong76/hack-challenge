import os
from ast import Assign
from multiprocessing.util import ForkAwareThreadLock
from unittest.mock import NonCallableMagicMock
from db import db, Asset, Job, Rating, User, Chat
from flask import Flask, request
import json
import users_dao
import datetime
from flask_socketio import SocketIO, emit, join_room
 
 
app = Flask(__name__)
db_filename = "hack.db"
 
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True
app.config['SECRET_KEY'] = 'mysecret'
socketio = SocketIO(app)

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
 
#-----------------AUTH/USERS--------------------------------------------

@app.route("/api/register/", methods=["POST"])
def register_account():
    """
    Endpoint for registering a new user
    """
    body = json.loads(request.data)
    email = body.get("email")
    password = body.get("password")
    first = body.get("first")
    last = body.get("last")
    phone_number = body.get("phone_number")
 
    if email is None or password is None or first is None or last is None  or phone_number is None:
        return failure_response("Missing first name, last name, email, password, or phone number", 400)
 
    success, user = users_dao.create_user(email, password, first, last, phone_number)
    if not success:
        return failure_response("User already exists", 400)
    user_serialize = user.serialize()
    #user_serialize["session_token"] = user.session_token
    #user_serialize["session_expiration"] = str(user.session_expiration)
    #user_serialize["update_token"] = user.update_token

    return success_response(user_serialize, 201)
 
 
 
@app.route("/api/login/", methods=["POST"])
def login():
    """
    Endpoint for logging in a user
    """
    body = json.loads(request.data)
    email = body.get("email")
    password = body.get("password")
 
    if email is None or password is None:
        return failure_response("Missing password or email", 400)
 
    success, user = users_dao.verify_credentials(email, password)
 
    if not success:
        return failure_response("Incorrect email or password", 401)
    
    user_serialize = user.serialize()
    return success_response(user_serialize)
 
 
@app.route("/api/session/", methods=["POST"])
def update_session():
    """
    Endpoint for updating a user's session
    """
    success, update_token = extract_token(request)
    success_user, user = users_dao.renew_session(update_token)
 
    if not success_user:
        return failure_response("Invalid update token", 400)
   
    return success_response(
        {
            "session_token": user.session_token,
            "session_expiration": str(user.session_expiration),
            "update_token": user.update_token
        }
    )
 
 
@app.route("/api/secret/", methods=["GET"])
def secret_message():
    """
    Endpoint for verifying a session token and returning a secret message
 
    In your project, you will use the same logic for any endpoint that needs
    authentication
    """
    success, session_token = extract_token(request)
    if not success:
        return failure_response("Could not extract session token", 400)
   
    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response("Session token Invalid", 400)
 
    return success_response({"message": "You have successfully implemented sessions!"})
 
 
@app.route("/api/logout/", methods=["POST"])
def logout():
    """
    Endpoint for logging out a user
    """
    success, session_token = extract_token(request)
 
    if not success:
        return failure_response("Could not extract session token", 400)
 
    user = users_dao.get_user_by_session_token(session_token)
    if user is None or not user.verify_session_token(session_token):
        return failure_response("Invalid session token", 400)
 
    user.session_token = ""
    user.session_expiration = datetime.datetime.now()
    user.update_token = ""
 
    return success_response({"message": "You have successfully logged out"})


@app.route("/api/user/")
def get_users():
    """
    Endpoint for the getting all users
    """
    user = [user.serialize() for user in User.query.all()]
    return success_response({"user": user})

@app.route("/api/user/<int:user_id>/", methods = ["POST"])
def update_user(user_id):
    """
    Endpoint for updating a user
    """
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return failure_response("User not found!")
    body = json.loads(request.data)
    first = body.get("first")
    last = body.get("last")
    email = body.get("email")
    phone_number = body.get("phone_number")
    if first is None or last is None or email is None or phone_number is None:
        return failure_response("Missing first name, last name, email, or phone number", 400)
    user.first = first 
    user.last = last 
    user.email = email 
    user.phone_number = phone_number 
    db.session.commit()
    return success_response(user.serialize(), 200)

@app.route("/api/user/<int:user_id>/")
def get_user(user_id):
    """
    Endpoint for getting a user by id
    """
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return failure_response("User not found!")
    return success_response(user.serialize())

@app.route("/api/user/<int:user_id>/", methods=["DELETE"])
def delete_user(user_id):
    """
    Endpoint for deleting a user by id
    """
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return failure_response("User not found!")
    db.session.delete(user)
    db.session.commit()
    return success_response(user.serialize())
    

#-----------------IMAGES--------------------------------------------

@app.route("/api/asset/")
def get_assets():
    """
    Endpoint for getting all assets
    """
    assets = [asset.serialize() for asset in Asset.query.all()]
    return success_response({"assets": assets})

@app.route("/api/user/<int:user_id>/upload/", methods=["POST"])
def upload_user(user_id):
    """
    Endpoint for uploading an image to AWS given its base64 form,
    then storing/returning the URL of that image for users
    """
    body = json.loads(request.data)
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return failure_response("User not found!")

    image_data = body.get("image_data")
    if image_data is None :
        return failure_response("No base64 image found")
    
    asset = Asset(image_data = image_data, user_id = user_id)
    db.session.add(asset)
    db.session.commit()
    return success_response(asset.serialize(), 201)

@app.route("/api/job/<int:job_id>/upload/", methods=["POST"])
def upload_job(job_id):
    """
    Endpoint for uploading an image to AWS given its base64 form,
    then storing/returning the URL of that image for jobs
    """
    body = json.loads(request.data)
    image_data = body.get("image_data")
    job = Job.query.filter_by(id = job_id).first()
    if job is None:
        return failure_response("Jser not found!")
    if image_data is None:
        return failure_response("No base64 image found")
    
    asset = Asset(image_data = image_data, job_id = job_id)
    db.session.add(asset)
    db.session.commit()
    return success_response(asset.serialize(), 201)

@app.route("/api/asset/<int:asset_id>/")
def get_asset(asset_id):
    """
    Endpoint for getting a asset by id
    """
    asset = Asset.query.filter_by(id = asset_id).first()
    if asset is None:
        return failure_response("Asset not found!")
    return success_response(asset.serialize())

#-----------------JOBS--------------------------------------------

@app.route("/api/job/")
def get_jobs():
    """
    Endpoint for getting all jobs
    """
    jobs = [job.serialize() for job in Job.query.all()]
    return success_response({"jobs": jobs})

@app.route("/api/user/<int:user_id>/job/", methods=["POST"])
def create_job(user_id):
    """
    Endpoint for creating a job
    """
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return failure_response("User not found!")

    body = json.loads(request.data)
    title = body.get("title")
    description = body.get("description")
    location = body.get("location")
    date_activity = body.get("date_activity")
    duration = body.get("duration")
    reward = body.get("reward")
    if title is None or description is None or  location is None or  date_activity is None or duration is None or reward is None:
        return failure_response("Missing one of the required fields", 400)
    job = Job(title = title, description = description, location = location, date_activity =date_activity, duration=duration, reward=reward, poster = user)
    db.session.add(job)
    db.session.commit()
    return success_response(job.serialize(), 201)

@app.route("/api/user/<int:user_id>/job/<int:job_id>/", methods= ["POST"])
def add_job(user_id, job_id):
    """
    Endpoint for adding a potential to a job
    """
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return failure_response("User not found!")

    job = Job.query.filter_by(id = job_id).first()
    if job is None:
        return failure_response("Job not found!")

    if user in job.potential:
        return failure_response("User already added this job!")

    job.potential += [user]
    db.session.commit()
    return success_response(user.serialize(), 201)

@app.route("/api/job/<int:job_id>/user/<int:user_id>/", methods= ["POST"])
def pick_receiver(job_id, user_id):
    """
    Endpoint for jobs to pick a empolyer
    """
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return failure_response("User not found!")

    job = Job.query.filter_by(id = job_id).first()
    if job is None:
        return failure_response("Job not found!")
    
    if user not in job.potential:
        return failure_response("This user did not add this job to his/her list!")
    
    if job not in user.job_as_potential:
        return failure_response("errorrrrrr")

    user.job_as_potential.remove(job)
    job.receiver = [user]
    job.taken = True
    db.session.commit()

    return success_response(job.serialize(), 201)

@app.route("/api/job/<int:job_id>/", methods = ["POST"])
def update_job(job_id):
    """
    Endpoint for updating a job
    """
    job = Job.query.filter_by(id = job_id).first()
    if job is None:
        return failure_response("Job not found!")
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

#-----------------RATINGS--------------------------------------------

@app.route("/api/rating/")
def get_ratings():
    """
    Endpoint for getting all ratings
    """
    ratings = [rating.serialize() for rating in Rating.query.all()]
    return success_response({"ratings": ratings})

@app.route("/api/user/<int:user_id>/rating/<int:user2_id>/", methods=["POST"])
def create_rating(user_id, user2_id):
    """
    Endpoint for creating a rating where first user rates second user
    """
    body = json.loads(request.data)
    rate = body.get("rate")
    description = body.get("description")
    if rate is None or description is None:
        return failure_response("Missing one of the required fields", 400)

    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return failure_response("User not found!")

    user2 = User.query.filter_by(id = user2_id).first()
    if user2 is None:
        return failure_response("User not found!")

    rating = Rating(rate = rate, description = description, poster = user, postee = user2)
    db.session.add(rating)
    db.session.commit()
    return success_response(rating.serialize(), 201)

@app.route("/api/user/<int:user_id>/rating/<int:rating_id>/", methods = ["POST"])
def update_rating(user_id, rating_id):
    """
    Endpoint for updating a rating
    """
    rating = Rating.query.filter_by(id = rating_id).first()
    if rating is None:
        return failure_response("Rating not found!")
    
    user = User.query.filter_by(id = user_id).first()
    if user is None:
        return failure_response("User not found!")
    
    if user not in rating.poster:
        return failure_response("User did not make this rating post!")

    body = json.loads(request.data)
    rate = body.get("rate")
    description = body.get("description")
    if rate is None or description is None:
        return failure_response("Missing one of the required fields", 400)
    rating.rate = rate 
    rating.description = description 
    db.session.commit()
    return success_response(rating.serialize(), 201)

@app.route("/api/rating/<int:rating_id>/")
def get_rating(rating_id):
    """
    Endpoint for getting a rating by id
    """
    rating = Rating.query.filter_by(id = rating_id).first()
    if rating is None:
        return failure_response("Rating not found!")
    return success_response(rating.serialize())

@app.route("/api/rating/<int:rating_id>/", methods=["DELETE"])
def delete_rating(rating_id):
    """
    Endpoint for deleting a rating by id
    """
    rating = Rating.query.filter_by(id = rating_id).first()
    if rating is None:
        return failure_response("Rating not found!")
    db.session.delete(rating)
    db.session.commit()
    return success_response(rating.serialize())

@socketio.on('message', namespace="/api/chat/")
def handleMessage(info):
    """
    Handles socketio messaging
    """
    time = datetime.datetime.now()
    message = Chat(sender_id = info['sender_id'], receiver_id = info['receiver_id'], message = info['msg'], time = time)
    session.add(message)
    session.commit()
    print('Message: ' + info['msg'])
    if info['sender_id'] < info['receiver_id']:
        room = (str(info['sender_id']) + ' ' + str(info['receiver_id']))
    else:
        room = join_room(str(info['receiver_id']) + ' ' + str(info['sender_id']))
    emit('private_message', message.serialize(), json=True, room = room)

@socketio.on('connect', namespace="/api/chat/")
def get_chat(info):
    """
    Handles socketio for getting all messages between users
    """
    sender = User.query.filter_by(id = info['user1_id'])
    if sender is None: 
        return failure_response("User 1 not found", 400)
    receiver = User.query.filter_by(id = info['user2_id'])
    if receiver is None: 
        return failure_response("User 2 not found", 400)
    sent_messages = Chat.query.filter_by(sender_id=info['user1_id'], receiver_id=info['user2_id']).order_by(Chat.time).all()
    received_messages = Chat.query.filter_by(sender_id=info['user2_id'], receiver_id=info['user1_id']).order_by(Chat.time).all()
    new = []
    i = 0
    j = 0
    while (len(received_messages)>j and i < len(sent_messages)):
        if (received_messages[j].time < sent_messages[i].time):
            new.append(received_messages[j].serialize())
            j+=1
        else:
            new.append(sent_messages[i].serialize())
            i+=1
    if j<len(received_messages):
        new += received_messages
    else:
        new += sent_messages
    #connect
    if info['user1_id'] < info['user2_id']:
        room = (str(info['user1_id']) + ' ' + str(info['user2_id']))
    else:
        room = (str(info['user2_id']) + ' ' + str(info['user1_id']))
    join_room(room)
    emit('past_history' ,{'chat': new}, json=True, room=room)

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=8000, debug=True, allow_unsafe_werkzeug=True)