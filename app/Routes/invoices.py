from flask import Blueprint, jsonify, session, request, render_template
from app.models import Invoice, User, Customer, db
from .authentication import login_is_required
from datetime import datetime
from ..templates import *


invoices = Blueprint('invoices', __name__)

@invoices.route('/view_invoice', methods=['GET'])
@login_is_required
def user_invoices():
    google_id = session.get('google_id')
    
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        return jsonify({"error": "user not found"}), 404
    
    userInvoices = Invoice.query.filter_by(user_id=user.id).all()
    invoices_data = [{
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "customer_name": invoice.customer.name,
        "amount": float(invoice.amount),
        "date_issued": invoice.date_issued.isoformat(),
        "due_date": invoice.due_date.isoformat(),
        "status": invoice.status
    } for invoice in userInvoices
    ]
    
    return render_template('invoice.html', invoices_data=invoices_data)

@invoices.route('/add_invoice', methods=['POST'])
@login_is_required
def create_invoice():
    data = request.get_json()
    invoice_number = data.get('invoice_number')
    customer_id = data.get('customer_id')
    amount = data.get('amount')
    date_issued = data.get('date_issued')
    due_date = data.get('due_date')
    
    if not all([invoice_number, customer_id, amount, date_issued, due_date]):
        return jsonify({"error": "all fields required"}), 400
    
    google_id = session.get('google_id')
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        return jsonify({"error": "user not found"}), 404
    
    customer = Customer.query.get(customer_id)
    if not customer or customer.user_id != user.id:
        return jsonify({"error": "invalid customer"}), 400
    
    newInvoice = Invoice(
        user_id=user.id,
        invoice_number=invoice_number,
        customer_id=customer_id,
        amount=amount,
        date_issued=datetime.strptime(date_issued, "%Y-%m-%d").date(),
        due_date=datetime.strptime(due_date, "%Y-%m-%d").date()
    )
    db.session.add(newInvoice)
    db.session.commit()
    
    return jsonify({"message": f"invoice {invoice_number} has been created"}), 201

@invoices.route('/invoice/<int:invoice_id>', methods=['GET'])
@login_is_required
def view_invoice(invoice_id):
    google_id = session.get('google_id')
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        return jsonify({"error": "user not found"}), 404
    
    invoice = Invoice.query.filter_by(id=invoice_id, user_id=user.id).first()
    
    if not invoice:
        return jsonify({"error": "invoice not found"}), 404
    
    
    invoice_data = {
        "number": invoice.invoice_number,
        "company_name": user.company_name or "Your Company Name",
        "company_email": user.email,
        "client_name": invoice.customer.name,
        "total": float(invoice.amount),
        "due_date": invoice.due_date.strftime("%Y-%m-%d"),
        "payment_method": invoice.payment_method or "Bank Transfer"
    }
    


