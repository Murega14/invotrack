from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify, session
from app.models import db, Customer, User, Invoice
from .authentication import login_is_required
from ..templates import *
import random

customers = Blueprint('customers', __name__)


@customers.route('/register', methods=['GET', 'POST'])
@login_is_required
def register_customer():
    if request.method == 'POST':
        google_id = session.get('google_id')
    
        user = User.query.filter_by(google_id=google_id).first()
    
        if not user:
            return jsonify({"error": "user not found"}), 404   
        
        name = request.form.get('name')
        email = user.email
        phone_number = request.form.get('phone_number')

        new_customer = Customer(
            user_id=user.id,
            name=name,
            email=email,
            phone_number=phone_number
        )

        db.session.add(new_customer)
        db.session.commit()

        flash('Business registered successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template('customer.html')