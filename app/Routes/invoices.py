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


@invoices.route('/view_invoice', methods=['GET'])
@login_is_required
def user_invoices():
    """Returns a list of user invoices"""
    try:
        google_id = session.get('google_id')
        if not google_id:
            logger.error("No google_id in session")
            return jsonify({"error": "Not authenticated"}), 401
            
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            logger.error(f"User not found: {google_id}")
            return jsonify({"error": "User not found"}), 404
        
        customer = Customer.query.filter_by(user_id=user.id).first()
        if not customer:
            logger.error(f"Customer profile not found for user ID: {user.id}")
            return redirect(url_for("customers.register"))
        
        try:
            invoices = Invoice.query.filter_by(user_id=user.id).all()
            if not invoices:
                generate_random_invoices(user_id=user.id, customer_id=customer.id)
                invoices = Invoice.query.filter_by(user_id=user.id).all()
            
            invoices_data = []
            for invoice in invoices:
                try:
                    invoice_data = {
                        "id": invoice.id,
                        "invoice_number": invoice.invoice_number,
                        "business_name": customer.name,
                        "amount": float(invoice.amount),
                        "date_issued": invoice.date_issued.isoformat(),
                        "due_date": invoice.due_date.isoformat(),
                        "status": invoice.status
                    }
                    invoices_data.append(invoice_data)
                except Exception as e:
                    logger.error(f"Error processing invoice {invoice.id}: {str(e)}")
                    continue
            
            return render_template('invoice.html', invoices_data=invoices_data)
            
        except Exception as e:
            logger.error(f"Error querying invoices: {str(e)}")
            raise
            
    except Exception as e:
        logger.error(f'Failed to fetch user invoices: {str(e)}')
        return jsonify({"error": "Internal server error"}), 500


@invoices.route('/invoice/<int:id>', methods=['GET'])
@login_is_required
def view_invoice(id: int):
    """Return the details of a single invoice
    Args:
        id (int): unique identifier of an invoice
    Returns:
        Response: HTML page with the invoice details or a JSON error message
    """
    try:
        google_id = session.get('google_id')
        if not google_id:
            logger.error("No google_id in session")
            return jsonify({"error": "Not authenticated"}), 401
            
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            logger.error(f"User not found: {google_id}")
            return jsonify({"error": "User not found"}), 404
        
        invoice = Invoice.query.get(id)
        if not invoice:
            logger.error(f"Invoice not found: {id}")
            return jsonify({"error": "Invoice not found"}), 404
        
        if invoice.user_id != user.id:
            logger.error(f"Unauthorized access by {user.id} for invoice {id}")
            return jsonify({"error": "Unauthorized access"}), 403
        
        customer = Customer.query.get(invoice.customer_id)
        if not customer:
            logger.error(f"Customer not found for invoice {id}")
            return jsonify({"error": "Customer not found"}), 404
        
        invoice_data = {
            "id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "customer_name": customer.name,
            "customer_email": user.email,
            "amount": float(invoice.amount),
            "status": invoice.status,
            "due_date": invoice.due_date.isoformat(),
            "date_issued": invoice.date_issued.isoformat()
        }
        
        return render_template('single_invoice.html', invoice_data=invoice_data, id=id)
    
    except Exception as e:
        logger.error(f"Failed to fetch invoice details: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@invoices.route('/invoice/<int:id>/mark-paid', methods=['PATCH'])
@login_is_required
def mark_as_paid(id: int):
    """Change invoice status to paid
    Args:
        id (int): invoice identifier
    Returns:
        Response: Redirect to the invoice view page or a JSON error message
    """
    try:
        google_id = session.get('google_id')
        if not google_id:
            logger.error("No google_id in session")
            return jsonify({"error": "Not authenticated"}), 401
            
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            logger.error(f"User not found: {google_id}")
            return jsonify({"error": "User not found"}), 404
        
        invoice = Invoice.query.get(id)
        if not invoice:
            logger.error(f"Invoice not found: {id}")
            return jsonify({"error": "Invoice not found"}), 404
            
        if invoice.user_id != user.id:
            logger.error(f"Unauthorized access by {user.id} for invoice {id}")
            return jsonify({"error": "Unauthorized access"}), 403
        
        invoice.status = "paid"
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to update invoice status: {str(e)}")
            raise
        
        return redirect(url_for('invoices.view_invoice', id=id))
    
    except Exception as e:
        logger.error(f"Failed to change invoice status: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@invoices.route('/add_invoice', methods=['POST'])
@login_is_required
def create_invoice():
    """Create a new invoice
    Returns:
        Response: JSON response indicating success or failure of invoice creation
    """
    try:
        google_id = session.get('google_id')
        if not google_id:
            logger.error("No google_id in session")
            return jsonify({"error": "Not authenticated"}), 401
            
        user = User.query.filter_by(google_id=google_id).first()
        if not user:
            logger.error(f"User not found: {google_id}")
            return jsonify({"error": "User not found"}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        required_fields = ['invoice_number', 'customer_id', 'amount', 'date_issued', 'due_date']
        if not all(field in data for field in required_fields):
            logger.error("Missing required fields")
            return jsonify({"error": "All fields are required"}), 400
        
        try:
            amount = float(data['amount'])
            date_issued = datetime.strptime(data['date_issued'], '%Y-%m-%d')
            due_date = datetime.strptime(data['due_date'], '%Y-%m-%d')
        except (ValueError, TypeError) as e:
            logger.error(f"Invalid data format: {str(e)}")
            return jsonify({"error": "Invalid data format"}), 400
            
        customer = Customer.query.get(data['customer_id'])
        if not customer:
            return jsonify({"error": "Customer not found"}), 404
            
        if customer.user_id != user.id:
            return jsonify({"error": "Unauthorized access to customer"}), 403
        
        new_invoice = Invoice(
            user_id=user.id,
            customer_id=data['customer_id'],
            invoice_number=data['invoice_number'],
            amount=amount,
            date_issued=date_issued,
            due_date=due_date,
            status="unpaid"
        )
        
        db.session.add(new_invoice)
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            logger.error(f"Failed to save new invoice: {str(e)}")
            raise
        
        logger.info(f"New invoice has been added: id {new_invoice.id}")
        return jsonify({
            "message": "Invoice added successfully",
            "invoice_id": new_invoice.id
        }), 201
                    
    except Exception as e:
        logger.error(f"Failed to create invoice: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500