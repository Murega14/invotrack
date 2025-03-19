from flask import Blueprint, jsonify, request
from ..models import db, Payment, User
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import logger

payments = Blueprint('payments', __name__)

@payments.route('/api/v1/payments/', methods=['GET'])
@jwt_required()
def get_payments():
    """
    Retrieve the list of payments made by the current user.
    This function fetches the payments associated with the user identified by the JWT token.
    It returns a JSON response containing the payment details or an error message if no payments
    are found or an exception occurs.
    Returns:
        Response: A Flask JSON response containing:
            - success (bool): Indicates if the operation was successful.
            - payments (list): A list of payment details if payments are found.
            - error (str): An error message if no payments are found.
            - message (str): A message indicating an internal server error.
            - error (str): The error message in case of an exception.
    """
    try:
        user_id = get_jwt_identity()
        
        payments = Payment.query.filter_by(payer_id=user_id).all()
        if not payments:
            return jsonify({"error": "no payments have been made by this user"}), 400
        
        payment_list = [{
            "id": payment.id,
            "amount": float(payment.amount),
            "payment_method": payment.payment_method,
            "transaction_code": payment.transaction_code,
            "payer": payment.payer.name if payment.payer else None,
            "payment_date": payment.payment_date.isoformat(),
            "invoice_id": payment.invoice_id,
        } for payment in payments]
        
        return jsonify({
            "success": True,
            "payments": payment_list
        }), 200
        
    except Exception as e:
        logger.error(f'endpoint error: {str(e)}')
        return jsonify({
            "message": "internal server error",
        }), 500