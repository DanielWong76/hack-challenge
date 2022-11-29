import datetime
import hashlib
import os

import bcrypt
from flask_sqlalchemy import SQLAlchemy
import base64
import boto3
import io
from io import BytesIO
from mimetypes import guess_type, guess_extension
from PIL import Image
import random
import re
import string

db = SQLAlchemy()

#-----------------TABLES-------------------------------------------
association_table_poster = db.Table("association_poster", db.Model.metadata,
    db.Column("job_id", db.Integer, db.ForeignKey("job.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
)

association_table_receiver = db.Table("association_receiver", db.Model.metadata,
    db.Column("job_id", db.Integer, db.ForeignKey("job.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
)

association_table_potential = db.Table("association_potential", db.Model.metadata,
    db.Column("job_id", db.Integer, db.ForeignKey("job.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
)

association_table_rating_poster = db.Table("association_rating_poster", db.Model.metadata,
    db.Column("rating_id", db.Integer, db.ForeignKey("rating.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
)

association_table_rating_postee = db.Table("association_rating_postee", db.Model.metadata,
    db.Column("rating_id", db.Integer, db.ForeignKey("rating.id")),
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"))
)

#-----------------USERS--------------------------------------------
class User(db.Model):
    """
    User model
    """
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True, autoincrement = True)

    # User information
    email = db.Column(db.String, nullable=False, unique=True)
    password_digest = db.Column(db.String, nullable=False)

    #Profile Info
    first = db.Column(db.String, nullable = False)
    last = db.Column(db.String, nullable = False)
    email = db.Column(db.String, nullable = False)
    phone_number = db.Column(db.Integer, nullable = False)
    images = db.relationship("Asset", cascade="delete")

    rating_as_poster = db.relationship("Rating", secondary=association_table_rating_poster, back_populates='poster')
    rating_as_postee = db.relationship("Rating", secondary=association_table_rating_postee, back_populates='postee')

    job_as_poster = db.relationship("Job", secondary=association_table_poster, back_populates='poster')
    job_as_receiver = db.relationship("Job", secondary=association_table_receiver, back_populates='receiver')
    job_as_potential = db.relationship("Job", secondary=association_table_potential, back_populates='potential')
    chat = db.relationship("Chat", cascade="delete")

    # Session information
    session_token = db.Column(db.String, nullable=False, unique=True)
    session_expiration = db.Column(db.DateTime, nullable=False)
    update_token = db.Column(db.String, nullable=False, unique=True)

    def __init__(self, **kwargs):
        """
        Initializes a User object
        """
        self.email = kwargs.get("email")
        self.password_digest = bcrypt.hashpw(kwargs.get("password").encode("utf8"), bcrypt.gensalt(rounds=13))
        self.first = kwargs.get("first")
        self.last = kwargs.get("last")
        self.email = kwargs.get("email")
        self.phone_number = kwargs.get("phone_number")
        self.renew_session()

    def serialize(self):
        """
        Serializes a User object
        """
        return {
            "id" : self.id,
            "email": self.email,
            "first" : self.first,
            "last" : self.last,
            "email" : self.email,
            "phone_number" : self.phone_number,
            "assets" :[i.simple_serialize() for i in self.images],
            "job_as_poster": [p.simple_serialize() for p in self.job_as_poster],
            "job_as_receiver": [r.simple_serialize() for r in self.job_as_receiver],
            "job_as_potential": [p.simple_serialize() for p in self.job_as_potential],
            "rating_as_poster": [r.simple_serialize() for r in self.rating_as_poster],
            "rating_as_postee":  [r.simple_serialize() for r in self.rating_as_postee]
        }

    def simple_serialize(self):
        """
        Serializes an Profile object without any other class
        """
        return {
            "id" : self.id,
            "first" : self.first,
            "last" : self.last,
        }

    def _urlsafe_base_64(self):
        """
        Randomly generates hashed tokens (used for session/update tokens)
        """
        return hashlib.sha1(os.urandom(64)).hexdigest()

    def renew_session(self):
        """
        Renews the sessions, i.e.
        1. Creates a new session token
        2. Sets the expiration time of the session to be a day from now
        3. Creates a new update token
        """
        self.session_token = self._urlsafe_base_64()
        self.session_expiration = datetime.datetime.now() + datetime.timedelta(days=1)
        self.update_token = self._urlsafe_base_64()

    def verify_password(self, password):
        """
        Verifies the password of a user
        """
        return bcrypt.checkpw(password.encode("utf8"), self.password_digest)

    def verify_session_token(self, session_token):
        """
        Verifies the session token of a user
        """
        return session_token == self.session_token and datetime.datetime.now() < self.session_expiration

    def verify_update_token(self, update_token):
        """
        Verifies the update token of a user
        """
        return update_token == self.update_token


#-----------------IMAGES--------------------------------------------

EXTENSIONS = ["png", "gif", "jpg", "jpeg"]
BASE_DIR = os.getcwd()
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
S3_BASE_URL = f"https://{S3_BUCKET_NAME}.s3.us-east-2.amazonaws.com"

class Asset(db.Model):
    """
    Asset Model
    """
    __tablename__ = "asset"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    base_url = db.Column(db.String, nullable = False)
    salt = db.Column(db.String, nullable = False)
    extension = db.Column(db.String, nullable = False)
    width = db.Column(db.Integer, nullable = False)
    height = db.Column(db.Integer, nullable = False)
    created_at = db.Column(db.DateTime, nullable = False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable = True)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable = True)

    def __init__(self, **kwargs):
        """
        Initializes an asset object
        """
        self.create(kwargs.get("image_data"), kwargs.get("user_id", None), kwargs.get("job_id", None))
    
    def create(self, image_data, user_id, job_id):
        """
        Given an image in base64 encoding, does the following
        1. Rejects the image if it is not a supported filetype
        2. Generate a random string for the image filename
        3. Decodes the image and attempts to upload to AWS
        """ 
        try:
            ext = guess_extension(guess_type(image_data)[0])[1:]
            if ext not in EXTENSIONS:
                raise Exception(f"Extension {ext} is not valid!")
            
            salt = "".join( #random generator creates filename
                random.SystemRandom().choice(
                    string.ascii_uppercase + string.digits
                )
                for _ in range(16)
            )
            
            img_str = re.sub("^data:image/.+;base64,", "", image_data)
            img_data = base64.b64decode(img_str)
            img = Image.open(BytesIO(img_data))

            self.base_url = S3_BASE_URL
            self.salt = salt
            self.extension = ext
            self.width = img.width
            self.height = img.height
            self.created_at = datetime.datetime.now()
            if user_id is not None:
                self.user_id = user_id
            if job_id is not None:
                self.job_id = job_id
            img_filename = f"{self.salt}.{self.extension}"
            self.upload(img, img_filename)
        except Exception as e:
            print(f"Error when creating image: {e}")
    
    def upload(self, img, img_filename):
        """
        Attempts to upload the image into the specified S3 bucket
        """
        try:
            #save image into temporary
            img_temp_loc = f"{BASE_DIR}/{img_filename}"
            img.save(img_temp_loc)

            #upload image into S3 bucket
            s3_client = boto3.client("s3")
            s3_client.upload_file(img_temp_loc, S3_BUCKET_NAME, img_filename)
            
            s3_resource = boto3.resource("s3")
            object_acl = s3_resource.ObjectAcl(S3_BUCKET_NAME, img_filename) 
            object_acl.put(ACL = "public-read")

            #remove img from temp location
            os.remove(img_temp_loc)
        except Exception as e:
            print(f"Error when uploading image: {e}")
        
    def serialize(self):
        """
        Serializes an asset object
        """
        return {
            "id" : self.id,
            "url": f"{self.base_url}/{self.salt}.{self.extension}",
            "created_at": str(self.created_at),
            "job_id": self.job_id,
            "user_id": self.user_id
        }
    
    def simple_serialize(self):
        """
        Serializes an asset object without relations
        """
        return {
            "id" : self.id,
            "url": f"{self.base_url}/{self.salt}.{self.extension}",
            "created_at": str(self.created_at),
        }
    
#-----------------JOBS--------------------------------------------

class Job(db.Model):
    """
    Job Model
    """
    __tablename__ = "job"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    title = db.Column(db.String, nullable = False)
    description = db.Column(db.String, nullable = False)
    location = db.Column(db.String, nullable = False)
    date_created = db.Column(db.DateTime, nullable = False)
    date_activity = db.Column(db.String, nullable = False)
    duration = db.Column(db.Integer, nullable = False)
    reward = db.Column(db.String, nullable = False)
    done = db.Column(db.Boolean, nullable = False)
    taken = db.Column(db.Boolean, nullable = False)
    poster = db.relationship("User", secondary=association_table_poster, back_populates='job_as_poster')
    receiver =  db.relationship("User", secondary=association_table_receiver, back_populates='job_as_receiver')
    images = db.relationship("Asset", cascade="delete")
    potential = db.relationship("User", secondary=association_table_potential, back_populates='job_as_potential')

    def __init__(self, **kwargs):
        """
        Initializes a job object
        """
        self.title = kwargs.get("title")
        self.description = kwargs.get("description")
        self.location = kwargs.get("location")
        self.date_created = datetime.datetime.now()
        self.date_activity = kwargs.get("date_activity")
        self.duration = kwargs.get("duration")
        self.reward = kwargs.get("reward")
        self.poster += [kwargs.get("poster")]
        self.done = False
        self.taken = False
    
    def serialize(self):
        """
        Serializes a job object
        """
        return{
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "date_created": str(self.date_created),
            "date_activity": self.date_activity,
            "duration": self.duration,
            "reward": self.reward,
            "done": self.done,
            "taken": self.taken,
            "asset": [i.simple_serialize() for i in self.images],
            "poster": [p.simple_serialize() for p in self.poster],
            "receiver": [r.simple_serialize() for r in self.receiver],
            "potential": [p.simple_serialize() for p in self.potential]
        }

    def simple_serialize(self):
        """
        Serializes a job object
        """
        return{
            "id": self.id,
            "title": self.title,
            "reward": self.reward,
            "done": self.done,
        }

#-----------------RATINGS--------------------------------------------
    
class Rating(db.Model):
    """
    Rating Model
    """
    __tablename__ = "rating"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    rate = db.Column(db.Integer, nullable = False)
    description = db.Column(db.String, nullable = False)
    
    poster = db.relationship("User", secondary=association_table_rating_poster, back_populates='rating_as_poster')
    postee = db.relationship("User", secondary=association_table_rating_postee, back_populates='rating_as_postee')

    def __init__(self, **kwargs):
        """
        Initializes a rating object
        """
        self.rate = kwargs.get("rate")
        self.description = kwargs.get("description")
        self.poster += [kwargs.get("poster")]
        self.postee += [kwargs.get("postee")]
    
    def serialize(self):
        return {
            "id" : self.id,
            "rate": self.rate,
            "description": self.description,
            "poster": [p.simple_serialize() for p in self.poster],
            "postee": [p.simple_serialize() for p in self.postee],
        }
    
    def simple_serialize(self):
        return {
            "id": self.id,
            "rate": self.rate,
            "description": self.description
        }

#--------------------Chat------------------------------------------
class Chat(db.Model):
    """
    Chat Model
    """
    __tablename__ = "chat"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    message = db.Column(db.String, nullable = False)
    sender_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    time = db.Column(db.DateTime, nullable=False)

    def __init__(self, **kwargs):
        """
        Creates a Chat object
        """
        self.sender_id = kwargs.get("sender_id")
        self.receiver_id = kwargs.get("receiver_id")
        self.message = kwargs.get("message")
        self.time = kwargs.get("time")

    def serialize(self):
        """
        Serializes a Chat Object
        """
        return {
            "id": self.id,
            "message": self.message,
            "time": self.time
        }


