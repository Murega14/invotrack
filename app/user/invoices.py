from flask import Blueprint, request, jsonify
from ..models import db, Invoice, InvoiceItem
from ..extensions import logger
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
from sqlalchemy.exc import SQLAlchemyError

invoices = Blueprint('invoices', __name__)

@invoices.route('/api/v1/invoices/create', methods=['POST'])
@jwt_required()
def create_invoice():
    try:
        user_id = get_jwt_identity()
        
        data = request.get_json()
        business_id = data.get('business_id')
        due_date = data.get('due_date')
        
        try:
            new_invoice = Invoice(
                issuer_id=user_id,
                business_id=business_id,
                status='pending',
                total_amount=0,
                date_issued=datetime.now(),
                due_date=due_date
            )
            db.session.add(new_invoice)
            db.session.flush()
        except SQLAlchemyError as e:
            logger.error('failed to create invoice: {str(e)}')
            db.session.rollback()
            return jsonify()
        
    except:
        pass