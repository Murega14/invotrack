from flask import (Blueprint, session, request, jsonify)
from functools import wraps
from flask_jwt_extended import create_access_token, create_refresh_token, get_jwt_identity
from ..extensions import logger, validate_password, generate_reset_token, verify_reset_token

business_auth = Blueprint('business_auth', __name__)

@business_auth.route('/api/v1/business/signup', methods=['POST'])
def signup_business():
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
        
        if Business.query.filter(Buyer.email==email).first():
            return jsonify({"error": "that email already exixts"}), 400
