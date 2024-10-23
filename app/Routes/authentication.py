import os
import json
import requests
from flask import Blueprint, session, abort, redirect, request, flash, url_for, render_template
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
from dotenv import load_dotenv
from app.models import Customer, db, User, OAuthSession
from datetime import datetime
from functools import wraps
import tempfile

load_dotenv()

authentication = Blueprint("authentication", __name__)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

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


@authentication.route('/user_profile', methods=['GET', 'POST'])
@login_is_required
def user_profile():
    google_id = session.get('google_id')
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('authentication.login'))
    
    customer = Customer.query.filter_by(email=user.email).first()
    
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')
        
        if not phone_number:
            flash('Phone number is required', 'error')
        else:
            if not customer:
                customer = Customer(name=user.name, email=user.email, phone_number=phone_number)
                db.session.add(customer)
            else:
                customer.phone_number = phone_number
            
            try:
                db.session.commit()
                flash('User details updated successfully', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'error')
        
        return redirect(url_for('authentication.user_profile'))
    
    return render_template('profile.html', user=user, customer=customer)