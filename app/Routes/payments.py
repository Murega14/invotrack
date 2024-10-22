from ..models import *
from .authentication import login_is_required
from flask import render_template, flash, url_for, Blueprint
from datetime import datetime
import random

payments = Blueprint('payments', __name__)


def generate_payments(user_id):
    paid_invoices = Invoice.query.filter(user_id=user_id, status='paid').all()
    
    for invoice in paid_invoices:
        existing_payment = Payment.query.filter_by(invoice_id=invoice.id).first()
        if existing_payment:
            continue
        
        payment_method = random.choice(['Family Bank', 'Coop Bank', 'Mpesa'])
        transaction_code = f"SJBC{random.randint(1000, 9999)}"
        
        new_payment = Payment(
            user_id=user_id,
            invoice_id=invoice.id,
            payment_method=payment_method,
            transaction_code=transaction_code,
            amount=invoice.amount,
            payment_date=datetime.utcnow()
        )
        
        db.session.add(new_payment)
        
    db.session.commit()