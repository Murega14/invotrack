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
    """
    Registers a new business for the authenticated user.
    This function performs the following steps:
    1. Retrieves the user ID from the JWT token.
    2. Extracts the business details (name, email, phone number) from the request JSON.
    3. Validates that all required fields are provided.
    4. Checks if a business with the same name already exists.
    5. Validates the provided email and phone number.
    6. Creates a new business entry in the database.
    7. Returns a success response if the business is created successfully.
    Returns:
        Response: A JSON response indicating the success or failure of the operation.
        HTTP Status Code: 200 if the business is created successfully, otherwise an appropriate error code.
    """
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
    """
    Fetches and returns a list of businesses based on the provided query parameters.
    If a 'name' query parameter is provided, it filters businesses whose names contain the given value.
    Otherwise, it returns all businesses.
    Returns:
        tuple: A tuple containing a JSON response with business details and an HTTP status code.
            - On success: (jsonify(business_details), 200)
            - On failure: (jsonify({"error": "internal server error"}), 500)
    Business details include:
        - id (int): The unique identifier of the business.
        - name (str): The name of the business.
        - owner (str or None): The name of the business owner, if available.
        - email (str): The email address of the business.
        - phone_number (str): The phone number of the business.
    Logs:
        Logs any exceptions that occur during the execution of the function.
    """
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
    """
    Fetches the details of a single business by its ID.
    Args:
        id (int): The ID of the business to fetch.
    Returns:
        tuple: A tuple containing a JSON response with the business details and an HTTP status code.
               On success, returns a JSON object with the business details and a 200 status code.
               On failure, returns a JSON object with an error message and a 500 status code.
    Raises:
        Exception: If there is an error fetching the business details.
    """
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
    """
    Update the details of a business.
    Args:
        id (int): The ID of the business to update.
    Returns:
        Response: A JSON response indicating the success or failure of the update operation.
    Raises:
        Exception: If an unexpected error occurs during the update process.
    The function performs the following steps:
    1. Retrieves the user ID from the JWT token.
    2. Fetches the business by ID from the database.
    3. Checks if the current user is the owner of the business.
    4. Validates and updates the business details based on the provided JSON data.
    5. Commits the changes to the database.
    6. Handles and logs any errors that occur during the process.
    Possible JSON response codes:
        - 200: Business details have been updated successfully.
        - 400: Input validation failed or database error occurred.
        - 403: Unauthorized access.
        - 500: Internal server error.
    """
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
    """
    Deletes a business by its ID.
    This function attempts to delete a business record from the database
    based on the provided business ID. It first checks if the current user
    is authorized to delete the business. If authorized, it deletes the
    business and commits the transaction. If any errors occur during the
    process, appropriate error messages are returned.
    Args:
        id (int): The ID of the business to be deleted.
    Returns:
        Response: A JSON response indicating the success or failure of the
        deletion operation, along with the appropriate HTTP status code.
    Raises:
        Exception: If an unexpected error occurs during the process.
    """
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