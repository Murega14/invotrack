import os
import pathlib
import requests
from flask import Blueprint, session, abort, redirect, request
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from dotenv import load_dotenv
from app.models import Customer, db
import jsonify

load_dotenv()

authentication = Blueprint("authentication", __name__)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://localhost/callback"

)

def login_is_required(function):
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)
        else:
            return function()
    return wrapper

@authentication.route('/login')
@authentication.route('/signup')
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)

@authentication.route('/callback')
def callback():
    flow.fetch_token(authorization_token=request.url)
    if not session["state"] == request.args["state"]:
        return abort(500)
    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)
    id_info = id_token.verify_oauth2_token(id_token=credentials._id_token,
                                           request=token_request,
                                           audience=GOOGLE_CLIENT_ID)
    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    return redirect("/home")

@authentication.route("/logout")
@login_is_required
def logout():
    session.clear()
    return redirect("/login")

@authentication.route('/user_profile', methods=['POST'])
def user_profile():
    flow.fetch_token(authorization_token=request.url)
    if not session["state"] == request.args["state"]:
        return abort(500)
    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)
    id_info = id_token.verify_oauth2_token(id_token=credentials._id_token,
                                           request=token_request,
                                           audience=GOOGLE_CLIENT_ID)
    data = request.get_json()
    name = id_info.get("name")
    email = id_info.get("email")
    phone_number = data.get("phone_number")
    
    customer =Customer(name=name, email=email, phone_number=phone_number)
    db.session.add(customer)
    db.session.commit()
    
    return jsonify({"message": "user details added successfully"}), 201 