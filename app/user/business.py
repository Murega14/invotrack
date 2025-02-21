from flask import Blueprint, request, jsonify
from ..extensions import logger
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models import Business, db
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.exc import SQLAlchemyError

business = Blueprint('business', __name__)

@business.route('/api/v1/business/register', methods=['POST'])
@jwt_required()
def register_business():
    try:
        user_id = get_jwt_identity()
        
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        
        if not all([name, email, phone_number]):
            return jsonify({"error": "all fields are required"}), 400
        
        if Business.query.filter_by(name=name).first():
            return jsonify({"Error": "name of business already exists"}), 400
        
        try:
            validate_email(email)
        except EmailNotValidError as e:
            return jsonify({"error": str(e)}), 400
        
        try:
            new_business = Business(name=name, email=email, phone_number=phone_number, owner_id=user_id)
            db.session.add(new_business)
            db.session.commit()
        except SQLAlchemyError as e:
            logger.error(f"failed to create new business: {str(e)}")
            db.session.rollback()
            return jsonify({"error": "failed to create a new business"}), 400
        
        response = jsonify({
            "success": True,
            "message": "business added successfully"
        })
        
        return response, 200
    
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({"error": str(e)}), 500
        
@business.route('/api/v1/businesses', methods=['GET'])
def view_businesses():
    try:
        name = request.args.get('name')
        if name:
            businesses = Business.query.filter(Business.name.like('%' + name + '%')).all()
        else:
            businesses = Business.query.all()
        
        business_details = [{
            "id": business.id,
            "name": business.name,
            "owner": business.user.name if business.user else None,
            "email": business.email,
            "phone_number": business.phone_number
        } for business in businesses]
        
        return jsonify(business_details), 200
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({"error": "internal server error"}), 500