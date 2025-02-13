from ..models import *
from .authentication import login_is_required
from flask import render_template, flash, url_for, Blueprint, session, redirect
from datetime import datetime, timedelta
import random
from ..templates import *

payments = Blueprint('payments', __name__)


def generate_payments(user_id):
    """
    Generate payments for the given user.

    :type user_id: int
    If a payment already exists for an invoice, it is skipped.

    :param user_id: The ID of the user for whom to generate payments
    :type user_id: int
    :return: None
    """
    user = User.query.filter_by(id=user_id).first()
    
    paid_invoices = Invoice.query.filter_by(user_id=user.id, status='paid').all()
    
    for invoice in paid_invoices:
        existing_payment = Payment.query.filter_by(invoice_id=invoice.id).first()
        if existing_payment:
            continue
        
        payment_method = random.choice(['Family Bank', 'Coop Bank', 'Mpesa'])
        transaction_code = f"SJBC{random.randint(1000, 9999)}"
        payment_date = datetime.today() - timedelta(days=random.randint(0, 30))
        
        new_payment = Payment(
            user_id=user_id,
            invoice_id=invoice.id,
            payment_method=payment_method,
            transaction_code=transaction_code,
            amount=invoice.amount,
            payment_date=payment_date
        )
        
        db.session.add(new_payment)
        
    db.session.commit()
    
@payments.route('/view_payments', methods=['GET'])
@login_is_required
def view_payments():
    """
    View the payments for the logged-in user.

    Retrieves the payments associated with the logged-in user and renders the payment.html template.

    :return: Rendered HTML page with payment data
    :rtype: str
    """
    google_id = session.get('google_id')
    user = User.query.filter_by(google_id=google_id).first()
    
    if not user:
        flash('user not found')
        return redirect('/login')
    
    payments = Payment.query.filter_by(user_id=user.id).all()
    
    if len(payments) == 0:
        generate_payments(user_id=user.id)
        payments = Payment.query.filter_by(user_id=user.id).all()
        
    payment_data = [{
        "id": payment.id,
        "invoice_number": payment.invoice.invoice_number,
        "customer_name": payment.user.name,
        "amount": float(payment.amount),
        "transaction_code": payment.transaction_code,
        "payment_method": payment.payment_method,
        "payment_date": payment.payment_date.isoformat()
    } for payment in payments
    ]
    
    return render_template('payment.html', payment_data=payment_data)
