from flask import Blueprint, jsonify, session, request, render_template, redirect, url_for
from app.models import Invoice, User, Customer, db
from .authentication import login_is_required
from datetime import datetime
from ..templates import *
import random
from datetime import timedelta
import logging

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
        date_issued = datetime.today() - timedelta(days=random.randint(0, 30))
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
    
    db.session.commit()


@invoices.route('/view_invoice', methods=['GET'])
@login_is_required
def user_invoices():
    """
    returns a list of user invoices
    """
    try:
        google_id = session.get('google_id')
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            logger.error(f"user not found: {google_id}")
            return jsonify({"error": "user not found"}), 404
        
        customer = Customer.query.filter_by(user_id=user.id).first()
        if not customer:
            logger.error(f"customer profile not found for user {user.id}")
            return redirect("/customers/register")
        
        invoices = Invoice.query.filter_by(user_id=user.id).all()
        if len(invoices) == 0:
            generate_random_invoices(user_id=user.id, customer_id=customer.id)
            invoices = Invoice.query.filter_by(user_id=user.id).all()
        
        invoices_data = [{
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "business_name": invoice.customer.name,
            "amount": float(invoice.amount),
            "date_issued": invoice.date_issued.isoformat(),
            "due_date": invoice.due_date.isoformat(),
            "status": invoice.status
        } for invoice in invoices]
        
        return render_template('invoice.html', invoices_data=invoices_data)
        
    except Exception as e:
        logger.error(f'failed to fetch user invoices: {str(e)}')
        return jsonify({"error": "internal server error"}), 500

@invoices.route('/invoice/<int:id>', methods=['GET'])
@login_is_required
def view_invoice(id: int):
    """
    return the details of a single invoice

    Args:
        id (int): unique identifier of an invoice

    Returns:
        Response: HTML page with the invoice details or a JSON error message
    """
    try:
        google_id = session.get('google_id')
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            logger.error(f"user not found: {google_id}")
            return jsonify({"error": "user not found"}), 400
        
        invoice = Invoice.query.get(id)
        if not invoice:
            logger.error(f"invoice not found: {id}")
            return jsonify({"error": "invoice not found"}), 404
        
        if invoice.user_id != user.id:
            logger.error(f"unauthorized access by {user.id} for invoice {id}")
            return jsonify({"error": "unauthorized access"}), 403
        
        invoice_data = {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "customer_name": invoice.customer.name,
            "customer_email": invoice.user.email,
            "amount": float(invoice.amount),
            "status": invoice.status,
            "due_date": invoice.due_date.isoformat(),
            "date_issued": invoice.date_issued.isoformat()
        }
        
        return render_template('single_invoice.html', invoice_data=invoice_data, id=id)
    
    except Exception as e:
        logger.error(f"failed to fetch invoice details: {str(e)}")
        return jsonify({"error": "internal server error"}), 500
        

@invoices.route('/invoice/<int:id>/mark-paid', methods=['PATCH'])
@login_is_required
def mark_as_paid(id: int):
    """
    change invoice status to paid

    Args:
        id (int): invoice identifier

    Returns:
        Response: Redirect to the invoice view page or a JSON error message
    """
    try:
        google_id = session.get('google_id')
        user = User.query.filter_by(google_id=google_id).first()
        
        if not user:
            logger.error(f"user not found: {google_id}")
            return jsonify({"error": "user not found"}),404
        
        invoice = Invoice.query.get(id)
        
        if not invoice:
            logger.error(f"invoice not found: {id}")
            return jsonify({"error": "invoice not found"})
        
        invoice.status = "paid"
        db.session.commit()
        
        return redirect(url_for('invoices.view_invoice', id=id))
    
    except Exception as e:
        logger.error(f"failed to change invoice status: {str(e)}")

@invoices.route('/add_invoice', methods=['POST'])
@login_is_required
def create_invoice():
    """
    creating a new invoice

    Returns:
        Response: JSON response indicating success or failure of invoice creation
    """
    try:
        google_id = session.get('google_id')
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            logger.error(f"user not found: {google_id}")
            return jsonify({"error": "user not found"}), 404
        
        data = request.get_json()
        invoice_number = data.get('invoice_number')
        customer_id = data.get('customer_id')
        amount = int(data.get('amount', 0))
        date_issued = data.get('date_issued')
        due_date = data.get('due_date')
        
        if not all([invoice_number, customer_id, amount, date_issued, due_date]):
            logger.error("not all fields have been submitted")
            return jsonify({"error": "all fields are required"}), 400
        
        formatted_date_issued = date_issued.strftime('%d/%m/%Y %H%M%S')
        formatted_due_date = due_date.strftime('%d/%m/%Y %H%M%S')
        
        new_invoice = Invoice(
            user_id=user.id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            amount=amount,
            date_issued=formatted_date_issued,
            due_date=formatted_due_date,
            status="unpaid"
        )
        db.session.add(new_invoice)
        db.session.commit()
        
        logger.info(f"new invoice has been added: id{new_invoice.id}")
        return jsonify({"success": "invoice added sucessfully"}), 201
                    
    except Exception as e:
        logger.error(f"failed to create invoice; {str(e)}")
        return jsonify({"error": "internal server error"}), 500



