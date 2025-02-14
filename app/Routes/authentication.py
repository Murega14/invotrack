import os
import json
import requests
from flask import Blueprint, session, abort, redirect, request, flash, url_for, render_template, jsonify, current_app
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from dotenv import load_dotenv
from app.models import Customer, db, User, OAuthSession
from datetime import datetime
from functools import wraps
import tempfile
import logging

load_dotenv()

authentication = Blueprint("authentication", __name__)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
client_secrets_data = os.getenv("CLIENT_SECRETS")

if not client_secrets_data:
    raise FileNotFoundError("CLIENT_SECRETS environment variable is not set or is empty")

try:
    client_secrets_dict = json.loads(client_secrets_data)
except json.JSONDecodeError as e:
    raise ValueError("CLIENT_SECRETS contains invalid JSON") from e

with tempfile.NamedTemporaryFile(delete=False, suffix=".json", mode='w') as temp_file:
    temp_file_path = temp_file.name
    json.dump(client_secrets_dict, temp_file)

flow = Flow.from_client_secrets_file(
    temp_file_path,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="https://invotrack-2.onrender.com/callback"
)

os.unlink(temp_file_path)


def login_is_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "google_id" not in session:
            return abort(401)
        else:
            return function(*args, **kwargs)
    wrapper.__name__ = function.__name__
    return wrapper

@authentication.route('/login')
@authentication.route('/signup')
def login():
    """
    login and signup endpoints using google oauth

    Returns:
        redirects to the callback endpoint
    """
    try:
        authorization_url, state = flow.authorization_url(prompt="consent")
        session["state"] = state
        return redirect(authorization_url)
    
    except Exception as e:
        logger.error(f"failed to login or signup: {str(e)}")

@authentication.route('/callback')
def callback():
    """
    callback _summary_

    _extended_summary_

    :return: _description_
    :rtype: _type_
    """
    try:
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
        
        email = id_info.get("email")
        user = User.query.filter_by(email=email).first()
        if not user:
            try:
                user = User(name=session["name"],
                        email=email,
                        google_id=session["google_id"])
                db.session.add(user)
                db.session.commit()
            
                return redirect("/customers/register")
            
            except Exception as e:
                logger.error(f"error adding new user to database: {str(e)}")
                db.session.rollback()
                return jsonify({"error": "failed to create user"}), 500
        
        return redirect("/dashboard")
    
    except Exception as e:
        logger.error(f"callback error: {str(e)}")
        return jsonify({"error": "internal server error"})

@authentication.route("/logout")
@login_is_required
def logout():
    """
    logs out the user

    Returns:
        deletes the session state
    """
    try:
        session.clear()
        return redirect('/')
    except Exception as e:
        logger.error(f"Failed to logout: {str(e)}")
        return jsonify({"error": "internal server error"}), 500


@authentication.route('/user_profile', methods=['GET', 'POST'])
@login_is_required
def user_profile():
    """
    shows the customer's details
    """
    try:
        google_id = session.get("google_id")
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            logger.error(f"user does not exist: {google_id}")
            return jsonify({"error": "user not found"}), 404
        
        email = user.email
        customer = Customer.query.filter_by(user_id=user.id).first()
        
        if not customer:
            logger.error(f"No business registered for user: {user.id}, {email}")
            return redirect('/customers/register')
        
        user_details = {
            "name": user.name,
            "email": user.email,
            "business_name": customer.name,
            "phone_number": customer.phone_number
        }
        
        return render_template('profile.html', user_details=user_details)
    
    except Exception as e:
        logger.error(f"Failed to fetch user details: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500