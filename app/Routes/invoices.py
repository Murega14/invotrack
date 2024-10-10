from flask import Blueprint, jsonify, session, request
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

@invoices.route('/add_invoice', methods=['POST'])
@login_is_required
def create_invoice():
    data = request.get_json()
    invoice_number = data.get('invoice_number')
    customer_name = data.get('customer_name')
    amount = data.get('amount')
    date_issued = data.get('date_issued')
    due_date = data.get('due_date')
    
    if not all([invoice_number, customer_name, amount, date_issued, due_date]):
        return jsonify({"error": "all fields required"}), 400
    
    newInvoice = Invoice(invoice_number=invoice_number,
                         customer_name=customer_name,
                         amount=amount,
                         date_issued=date_issued,
                         due_date=due_date)
    db.session.add(newInvoice)
    db.session.commit()
    
    return jsonify({"message": f"invoice {invoice_number} has been created"}), 201


