from flask import Blueprint, jsonify, session, abort
from app.models import Invoice, User, db
from .authentication import login_is_required

invoices = Blueprint('invoices', __name__)

@invoices.route('/invoices', methods=['GET'])
@login_is_required
def user_invoices():
    google_id = session.get('google_id')
    
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        return jsonify({"error": "user not found"}), 404
    
    userInvoices = Invoice.query.filter_by(user_id=user.id).all()
    invoices_data = [{
        "invoice_number": invoice.invoice_number,
        "customer_name": invoice.customer_name,
        "amount": invoice.amount,
        "date_issued": invoice.date_issued.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "status": invoice.status
    } for invoice in userInvoices
    ]
    
    return jsonify(invoices_data), 200

