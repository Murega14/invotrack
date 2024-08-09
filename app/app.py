from flask import Flask, request, jsonify
from flask_migrate import Migrate
from app.models import db, Customer, Invoice, Payment, User
import os
from datetime import datetime
from config import config
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_jwt_extended import get_jwt_identity
from dotenv import load_dotenv
from app.mpesa import sendStkPush

load_dotenv()

app = Flask(__name__)
config_name = os.getenv('FLASK_CONFIG', 'default')
app.config.from_object(config[config_name])

db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)


# Initialize database
with app.app_context():
    db.create_all()



@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "Username or email already exists"}), 400
    
    new_user = User(name=name, username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "User created successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('identifier')
    password = data.get('password')

    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    if user and user.check_password(password):
        login_user(user)
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

#@app.route('/logout', methods=['POST'])
#@login_required
#def logout():
#    logout_user()
#    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/invoices', methods=['POST', 'GET'])
def create_invoice():
    if request.method == 'GET':
        invoices = Invoice.query.all()
        return jsonify([invoice.to_dict() for invoice in invoices]), 200
    
    if request.method == 'POST':
        data = request.get_json()
        customer_name = data.get('customer_name')
        invoice_number = data.get('invoice_number')
        amount = data.get('amount')
        date_issued_str = data.get('date_issued')
        due_date_str = data.get('due_date')
        status = data.get('status')

        # Convert string dates to date objects
        try:
            date_issued = datetime.strptime(date_issued_str, '%d-%m-%Y').date()
            due_date = datetime.strptime(due_date_str, '%d-%m-%Y').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Please use DD-MM-YYYY."}), 400

        new_invoice = Invoice(customer_name=customer_name, invoice_number=invoice_number,
                            amount=amount, date_issued=date_issued,
                            due_date=due_date, status=status)
        db.session.add(new_invoice)
        db.session.commit()
        return jsonify({"message": "Invoice created successfully"}), 201

@app.route('/invoices/<int:invoice_number>', methods=['GET'])
#@jwt_required()
def get_invoice(invoice_number):
    #current_user.id = get_jwt_identity()
    invoice = Invoice.query.filter_by(invoice_number=invoice_number).first()
    if invoice:
        return jsonify(invoice.to_dict()), 200
    else:
        return jsonify({"error": "Invoice not found"}), 404

@app.route('/payments', methods=['GET', 'POST'])
def create_payment():
    if request.method == 'GET':
        payments = Payment.query.all()
        return jsonify([payment.to_dict() for payment in payments]), 201
    
    if request.method == 'POST':
        data = request.get_json()
        invoice_number = data.get('invoice_number')
        payment_method = data.get('payment_method')
        amount = data.get('amount')

        invoice = Invoice.query.filter_by(invoice_number=invoice_number).first()
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404

        payment = Payment(
            invoice_id=invoice.id,
            payment_method=payment_method,
            amount=amount
        )
        db.session.add(payment)
        db.session.commit()

        invoice.status = 'paid' if invoice.amount <= amount else 'unpaid'
        db.session.commit()

        return jsonify(payment.to_dict()), 201

@app.route('/customers', methods=['GET', 'POST'])
def get_customers():
    if request.method == 'GET':
        customers = Customer.query.all()
        return jsonify([customer.to_dict() for customer in customers]), 200
    
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')

        if not name or not email:
            return jsonify({"error": "Name and email are required"}), 400

        new_customer = Customer(name=name, email=email)
        db.session.add(new_customer)
        db.session.commit()
        return jsonify(new_customer.to_dict()), 201    


@app.route('/payment/mpesa', methods=['POST'])
def lipanaMpesa():
    sendStkPush()
    
print(f"Running in {config_name} mode")
print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")


if __name__ == '__main__':
    app.run(port=5555, debug=True)
