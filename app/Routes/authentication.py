import os
import pathlib
import requests
from flask import Blueprint, session, abort, redirect, request, jsonify
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from dotenv import load_dotenv
from app.models import Customer, db, User, OAuthSession
from datetime import datetime
from functools import wraps

load_dotenv()

authentication = Blueprint("authentication", __name__)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)

def login_is_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)
        else:
            return function()
    return wrapper

@authentication.route('/login')
@authentication.route('/signup')
def login():
    authorization_url, state = flow.authorization_url(prompt="consent")
    session["state"] = state
    return redirect(authorization_url)

@authentication.route('/callback')
def callback():
    flow.fetch_token(authorization_response=request.url)
    
    if not session["state"] == request.args["state"]:
        return abort(500)
    
    credentials = flow.credentials
    request_session = requests.sessions.Session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)
    
    id_info = id_token.verify_oauth2_token(id_token=credentials._id_token,
                                           request=token_request,
                                           audience=GOOGLE_CLIENT_ID)
    
    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    
    user = User.query.filter_by(email=id_info.get("email")).first()
    if not user:
        user = User(name=id_info.get("name"),
                    email=id_info.get("email"),
                    google_id=id_info.get("sub")
                    )
        db.session.add(user)
        db.session.commit()
        
    oauth_session = OAuthSession.query.filter_by(user_id=user.id).first()
    if oauth_session:
        oauth_session.access_token = credentials.token
        oauth_session.refresh_token = credentials.refresh_token
        oauth_session.token_expiry = credentials.expiry
        oauth_session.updated_at = datetime.now()
    else:
        oauth_session = OAuthSession(
            user_id=user.id,
            access_token=credentials.token,
            refresh_token=credentials.refresh_token,
            token_expiry=credentials.expiry
        )
        db.session.add(oauth_session)
        
    db.session.commit()
    
    return redirect("/dashboard")

@authentication.route("/logout")
@login_is_required
def logout():
    session.clear()
    return redirect("/login")

@authentication.route('/user_profile', methods=['POST'])
@login_is_required
def user_profile():
    data = request.get_json()
    name = session.get("name")
    email = session.get("google_id")
    phone_number = data.get("phone_number")
    
    customer = Customer(name=name, email=email, phone_number=phone_number)
    db.session.add(customer)
    db.session.commit()
    
    return jsonify({"message": "User details added successfully"}), 201
