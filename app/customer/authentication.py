from flask import (Blueprint, session, request, jsonify, redirect)
from functools import wraps
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity
from ..extensions import logger, validate_password, generate_reset_token, verify_reset_token, flow, GOOGLE_CLIENT_ID
import re
from email_validator  import validate_email, EmailNotValidError
from ..models import User, db
from datetime import timedelta
from sqlalchemy.exc import SQLAlchemyError
from google.oauth2 import id_token
from pip._vendor import cachecontrol
import google.auth.transport.requests
import requests

user_auth = Blueprint('user_auth', __name__)

@user_auth.route('/api/v1/user/signup', methods=['POST'])
def signup_user():
    try:
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        password = data.get('password')
        
        if not all([name, email, phone_number, password]):
            return jsonify({"error": "all fields are required"}), 400
        
        try:
            validate_email(email)
        except EmailNotValidError:
            return jsonify({"error": "invalid email format"}), 400
        
        if not validate_password(password):
            return jsonify({"error": "password must be atleast 8 characters containing an uppercase, lowercase letter and a number"}), 400
        
        if not re.match(r"\d{10}$", phone_number):
            return jsonify({"Error": "phone number must be 10 digits"}), 400
        
        if User.query.filter(User.email==email).first():
            return jsonify({"error": "that email already exixts"}), 400
        
        new_user = User(
            name=name,
            email=email,
            phone_number=phone_number,
            httponly=True,
            secure=True
        )
        new_user.hash_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        expires = timedelta(hours=2)
        access_token = create_access_token(identity=new_user.id, expires_delta=expires)
        
        response = jsonify({
            "success": True,
            "message": "Login successful",
            "access_token": access_token
        })
        response.set_cookie(
            "session_token",
            access_token,
        )
        
        return response, 200
    
    except (SQLAlchemyError, Exception) as e:
        logger.error(f"Failed to signup user: {str(e)}")
        db.rollback()
        return jsonify({"error": "internal server error"}), 500
    
@user_auth.route('/api/v1/user/google_signup', methods=['POST'])
def google_signup():
    try:
        authorization_url, state = flow.authorization_url(prompt="consent")
        session["state"] = state
        return redirect(authorization_url)
    
    except Exception as e:
        logger.error(f"failed to signup: {str(e)}")
        return jsonify({"error": "internal server error"}), 500
    
@user_auth.route('/callback', methods=['GET'])
def callback():
    try:
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        request_session = requests.sessions.Session()
        cached_session = cachecontrol.CacheControl(request_session)
        token_request = google.auth.transport.requests.Request(session=cached_session)
        
        
        id_info = id_token.verify_oauth2_token(
            id_token=credentials._id_token,
            request=token_request,
            audience=GOOGLE_CLIENT_ID
        )
        session["google_id"] = id_info.get("sub")
        session["name"] = id_info.get("name")
        email = id_info.get("email")
        
        user = User.query.filter_by(email=email).first()
        if not user:
            try:
                user = User(name=session["name"], email=email)
                user.hash_password(session["google_id"])
                db.session.add(user)
                db.session.commit()
            except SQLAlchemyError as e:
                logger.error(f"database error: {str(e)}")
                db.session.rollback()
                return jsonify({"error": "failed to create user"}), 500
        
        expires = timedelta(hours=2)
        access_token = create_access_token(identity=user.id, expires_delta=expires)
        
        response = jsonify({
            "success": True,
            "access_token": access_token,
            "message": "sign up successful"
        })
        response.set_cookie(
            "session_token",
            access_token
        )
        
        return response, 200
    
    except Exception as e:
        logger.error(f"Failed to complete Google OAuth2 login/signup: {str(e)}")
        return jsonify({"error": "internal server error"}), 500
    
@user_auth.route('/api/v1/user/login', methods=['GET'])
def login_user():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not all([email, password]):
            return jsonify({"error": "all fields are required"}), 400
        
        user = User.query.filter_by(email=email).first()
        if not user or user.check_hash(password):
            logger.error("invalid login credentials")
            return jsonify({"error": "invalid login credentials"}), 403
        
        expires = timedelta(hours=2)
        access_token = create_access_token(identity=user.id, expires_delta=expires)
        refresh_token = create_refresh_token(identity=user.id)
        
        response = jsonify({
            "sucess": True,
            "message": "login successful",
            "access_token": access_token,
            "refresh_token": refresh_token
        })
        response.set_cookie("session_token", refresh_token, secure=True)
        
        return response, 200
    
    except Exception as e:
        logger.error(f"failed to login user: {str(e)}")
        return jsonify({"error": "failed to login user"})

    
