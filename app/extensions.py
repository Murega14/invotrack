import logging
from itsdangerous import SignatureExpired, BadSignature, URLSafeTimedSerializer
from flask import current_app
import re
from google_auth_oauthlib import Flow
import tempfile
import os
from dotenv import load_dotenv
import json

load_dotenv()

logging = logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_reset_token(email):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt='password-reset-salt')

def verify_reset_token(token, expiration=1200):
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt='password-reset-salt',
            max_age=expiration
        )
        return email
    
    except (SignatureExpired, BadSignature) as e:
        logger.warning(f"invalid reset token: {str(e)}")
        return None
    
def validate_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    return True

def validate_phone_number(phone_number):
    if not re.search(r"\d{10}$", phone_number):
        return False
    return True

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
client_secrets_data = os.getenv("CLIENT_SECRETS")

try:
    client_secrets_dict = json.loads(client_secrets_data)
except json.JSONDecodeError as e:
    raise ValueError("client_Secrets contains invalid json") from e

with tempfile.NamedTemporaryFile(delete=False,suffix=".json", mode="w") as temp_file:
    temp_file_path = temp_file.name
    json.dump(client_secrets_dict, temp_file)
    
flow = Flow.from_client_secrets_file(
    temp_file_path,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="https://invotrack-2.onrender.com/callback"
)

os.unlink(temp_file_path)
