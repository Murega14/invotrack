from flask import Blueprint, request, jsonify
from ..extensions import logger, validate_phone_number
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
            validate_phone_number(phone_number)
        except:
            return jsonify({"Error": "phone number must be 10 digits"}), 400
        
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
    
@business.route('/api/v1/businesses/<int:id>', methods=['GET'])
def single_business(id: int):
    try:
        business = Business.query.get_or_404(id)
        
        business_detail = {
            "id": business.id,
            "name": business.name,
            "owner": business.user.name if business.name else None,
            "email": business.email,
            "phone_number": business.phone_number
        }
        
        return jsonify(business_detail), 200
    
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "failed to fetch business detail",
            "error": str(e)
        }), 500

@business.route('/api/v1/businesses/update/<int:id>', methods=['PUT'])
@jwt_required()
def update_business(id: int):
    try:
        user_id = get_jwt_identity()
        
        business = Business.query.get_or_404(id)
        
        if business.owner_id != user_id:
            return jsonify({"error": "unauthorized access"}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "input is required"}), 400
        
        try:
            if 'name' in data:
                business.name = data['name'].strip()
            if 'email' in data:
                try:
                    validate_email(data['email'])
                    business.email = data['email']
                except EmailNotValidError as e:
                    return jsonify({"error": str(e)}), 400
            if 'phone_number' in data:
                try:
                    validate_phone_number(data['phone_number'])
                    business.phone_number = data['phone_number']
                except:
                    return jsonify({"Error": "phone number must be 10 digits"}), 400
            
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "business details have been updated successfully"
            }), 200
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            db.session.rollback()
            return jsonify({
                "message": "failed to update business details",
                "error": str(e)
            }), 400
            
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500
        
@business.route('/api/v1/businesses/<int:id>/delete', methods=['DELETE'])
@jwt_required()
def delete_business(id: int):
    try:
        user_id = get_jwt_identity()
        
        business = Business.query.get_or_404(id)
        
        if business.owner_id != user_id:
            return jsonify({"error": "unauthorized access"}), 403
        
        try:
            db.session.delete(business)
            db.session.commit()
            
            return jsonify({
                "success": True,
                "message": "business has been deleted"
            }), 200
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            db.session.rollback()
            return jsonify({
                "message": "failed to delete business",
                "error": str(e)
            }), 400
            
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500