from flask import Blueprint, jsonify, session, request
from app.models import Customer, User, db
from .authentication import login_is_required

customers = Blueprint('customers', __name__)

@customers.route('/customers', methods=['POST', 'GET'])
@login_is_required
def add_customers():
    if request.method == 'POST':
        user_id = session.get('user_id')
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        
        if not all([name, email, phone_number]):
            return jsonify({"error": "Missing required fields"}), 400
        
        new_customer = Customer(name=name, email=email, phone_number=phone_number)
        db.session.add(new_customer)
        db.session.commit()
        
        return jsonify(new_customer.to_dict()), 201
    
    if request.method == 'GET':
        customers = Customer.query.all()
        return jsonify(customers.to_dict()), 200
    
@customers.route('/customers/<int:user_id>/invoices', methods=['GET'])
@login_is_required
def customer_invoices(user_id):
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User not found"}), 404
    
    customer = Customer.query.get(user_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    
    invoices = customer.invoices
    return jsonify(invoices.to_dict()), 200

@customers.route('/customers/<int:user_id>/payments', methods=['GET'])
@login_is_required
def customer_payments(user_id):
    user_id = session.get('user_id')
    
    if not user_id:
        return jsonify({"error": "User not found"}), 404
    
    customer = Customer.query.get(user_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    
    payments = customer.payments
    return jsonify(payments.to_dict()), 200
        
        