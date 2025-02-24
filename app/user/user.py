from flask import Blueprint, request, jsonify, session
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import logger
from email_validator import validate_email, EmailNotValidError
from ..models import db, User
from sqlalchemy.exc import SQLAlchemyError

user = Blueprint('user', __name__)

@user.route('/api/v1/user', methods=['GET'])
@jwt_required()
def user_details():
    try:
        user_id = get_jwt_identity()
        
        user = User.query.get_or_404(user_id)
        
        user_profile = {
            "id": user.id,
            "name": user.name,
            "email": user.email
        }
        
        return jsonify(user_profile), 200
    
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "failed to fetch user profile",
            "error": str(e)
        }), 500
        
@user.route('/api/v1/user/update', methods=['PUT'])
@jwt_required()
def update_user():
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(id)
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "input data is required"}), 400
        
        try:
            if 'name' in data:
                user.name = data['name']
            if 'email' in data:
                try:
                    email = data['email']
                    validate_email(email)
                    user.email = email
                except EmailNotValidError:
                    return jsonify({"Error": "invalid email"}), 400
            
            db.session.commit()
            return jsonify({
                "success": True,
                "message": "user profile updated successfully"
            }), 200
        except SQLAlchemyError as e:
            logger.error(f"database error: {str(e)}")
            db.session.rollback()
            return jsonify({
                "message": "failed to update user profile",
                "error": str(e)
            }), 400
            
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500
        
@user.route('/api/v1/user/delete', methods=['DELETE'])
@jwt_required()
def delete_user_profile():
    try:
        user_id = get_jwt_identity()
        user = User.query.get_or_404(user_id)
        
        try:
            db.session.delete(user)
            db.commit()
            
            session.clear()
            return jsonify({
                "success": True,
                "message": "user account deleted"
            }), 200

        except SQLAlchemyError as e:
            logger.error(f"database error: {str(e)}")
            db.session.rollback()
            return jsonify({
                "message": "failed to delete user profile",
                "error": str(e)
            }), 400
                
    except Exception as e:
        logger.error(f"endpoint error: {str(e)}")
        return jsonify({
            "message": "internal server error",
            "error": str(e)
        }), 500