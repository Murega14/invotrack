from flask import Blueprint, jsonify, session, request, render_template, redirect, url_for
from app.models import Invoice, User, Customer, db
from .authentication import login_is_required
from datetime import datetime, timedelta
import logging
import random

invoices = Blueprint('invoices', __name__)

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_random_invoices(user_id: int, customer_id: int, num_invoices=10):
    """Generate test dummy invoices
    Args:
        user_id (int): user identifier
        customer_id (int): business identifier
        num_invoices (int, optional): number of invoices to generate. Defaults to 10.
    """
    for _ in range(num_invoices):
        invoice_number = f"INV-{random.randint(1000, 9999)}"
        amount = round(random.uniform(100, 1000), 0)
        date_issued = datetime.now() - timedelta(days=random.randint(0, 30))
        due_date = date_issued + timedelta(days=random.randint(2, 5))
        status = random.choice(['unpaid', 'paid'])

        new_invoice = Invoice(
            user_id=user_id,
            invoice_number=invoice_number,
            customer_id=customer_id,
            amount=amount,
            date_issued=date_issued,
            due_date=due_date,
            status=status
        )
        db.session.add(new_invoice)
    
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to generate random invoices: {str(e)}")
        raise

@invoices.route('/invoices', methods=['GET'])
@login_is_required
def view_invoices():
    """
    _summary_
    """
    try:
        google_id = session.get('google_id')
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            logger.error(f"user not found: {google_id}")
            return jsonify({"error": "user not found"}), 404
        
        customer = Customer.query.filter_by(user_id=user.id).first_or_404("Customer not found")
        if not customer:
            return redirect('/customers/register')
        
        invoices = Invoice.query.filter_by(user_id=user.id, customer_id=customer.id).all()
        if len(invoices) == 0:
            generate_random_invoices(user_id=user.id, customer_id=customer.id)
            invoices = Invoice.query.filter_by(user_id=user.id, customer_id=customer.id)
            
        invoices_list =[{
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "customer_name": customer.name,
            "amount": float(invoice.amount),
            "date_issued": invoice.date_issued.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "status": invoice.status
        } for invoice in invoices]
        
        return render_template('invoice.html', invoices_data=invoices_list)
    
    except Exception as e:
        logger.error(f"failed to fetch invoices: {str(e)}")
        return jsonify({"error": "internal server error"}), 500
    
@invoices.route('/invoices/add', methods=['POST'])
@login_is_required
def create_invoice():
    """
    _summary_
    """
    try:
        pass
    except:
        pass
    
@invoices.route('/invoices/<int:id>', methods=['GET'])
@login_is_required
def view_single_invoice(id: int):
    """
    _summary_

    Args:
        id (int): _description_
    """
    try:
        google_id = session.get('google_id')
        user = User.query.filter_by(google_id=google_id).first_or_404("user not found")
        
        invoice = Invoice.query.get_or_404(id)
        
        if invoice.user_id != user.id:
            logger.error(f"user {user.id} does not own {id}")
            return jsonify({"error": "unauthorized access"}), 403
        
        invoice_data = {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "customer_name": invoice.customer.name,
            "customer_email": user.email,
            "amount": float(invoice.amount),
            "date_issued": invoice.date_issued.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "status": invoice.status
        }
        
        return render_template('single_invoice.html', invoice_data=invoice_data)
    
    except Exception as e:
        logger.error(f"failed to fetch invoice: {str(e)}")
        return jsonify({"error": "internal server error"}), 500
        
        