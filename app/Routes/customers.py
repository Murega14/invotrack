from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from app.models import db, Customer, User, Invoice
from .authentication import login_is_required
from ..templates import *
import logging

customers = Blueprint('customers', __name__)

logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@customers.route('/register', methods=['GET', 'POST'])
@login_is_required
def register_customer():
    """
    register a customer using the user's email
    """
    if request.method == 'POST':
        try:
            google_id = session.get("google_id")
            user = User.query.get(google_id)
            
            if not user:
                logger.error(f"user not found: {google_id}")
                return redirect('/login')
            
            name = request.form.get("name")
            email = user.email
            phone_number = request.form.get("phone_number")
            
            if not all([name, email, phone_number]):
                logger.error("not all fields have been submitted")
                flash('All fields are required', 'error')
                return jsonify({"error": "all fields are required"}), 403
            
            new_customer = Customer(name=name, email=email, phone_number=phone_number)
            db.session.add(new_customer)
            db.session.commit()
            
            flash('Business registered successfully', 'success')
            logger.info(f"Business registered; {new_customer.id}")
            return redirect('/dashboard')
        
        except Exception as e:
            logger.error(f"Failed to add business details: {str(e)}")
            db.session.rollback()
            return jsonify({"error": "internal server error"}), 500
    
    return render_template('customer.html')