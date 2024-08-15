from flask import Flask, request, jsonify
from flask_migrate import Migrate
from app.models import *
import os
from datetime import datetime
from config import config
from flask_jwt_extended import JWTManager, create_access_token, jwt_required
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_jwt_extended import get_jwt_identity
from dotenv import load_dotenv
from app.mpesa import *
from decimal import Decimal
from flask_mpesa import MpesaAPI
from flask_wtf.csrf import CSRFProtect
from functools import wraps

load_dotenv()

app = Flask(__name__)

#csrf = CSRFProtect(app)
mpesa_api = MpesaAPI(app)
config_name = os.getenv('FLASK_CONFIG', 'default')
app.config.from_object(config[config_name])
app.config["API_ENVIRONMENT"] = "sandbox" #sandbox or production
app.config["APP_KEY"] = 'vbxsneeZ9IMFoyKKIgOIQQZFlawAADnP' # App_key from developers portal
app.config["APP_SECRET"] = 'WAzDhQVhitIXwiTc' #App_Secret from developers portal

db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'

# Initialize database
with app.app_context():
    db.create_all()

def role_required(role_name):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user_id = get_jwt_identity()
            user = User.query.get(user_id)

            if any(role.name == role_name for role in user.roles):
                return func(*args, **kwargs)
            else:
                return jsonify({"error": "Unauthorized access"}), 400
        return wrapper
    return decorator

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    name = data.get('name')
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    role_name = data.get('role_name')

    if User.query.filter((User.username == username) | (User.email == email)).first():
        return jsonify({"error": "Username or email already exists"}), 400
    
    new_user = User(name=name, username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    role = Role.query.filter_by(name=role_name).first()
    if not role:
        return jsonify({'error': 'role not found'}), 400
    
    user_role = UserRoles(user_name=new_user.name, role_name=role.name)
    db.session.add(user_role)
    db.session.commit()

    return jsonify({"message": "User created successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    identifier = data.get('identifier')
    password = data.get('password')

    # Find the user by username or email
    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()
    
    # Check if user exists and the password is correct
    if user and user.check_password(password):
        login_user(user)
        access_token = create_access_token(identity=user.id)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401


@app.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"}), 200

@app.route('/invoices', methods=['POST', 'GET'])
@jwt_required()
@role_required('Admin')
def create_invoice():
    current_user.id = get_jwt_identity()
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
@jwt_required()
def get_invoice(invoice_number):
    current_user.id = get_jwt_identity()
    invoice = Invoice.query.filter_by(invoice_number=invoice_number).first()
    if invoice:
        return jsonify(invoice.to_dict()), 200
    else:
        return jsonify({"error": "Invoice not found"}), 404
        
@app.route('/payments', methods=['GET', 'POST'])
@jwt_required()
@role_required('Admin')
def create_payment():
    current_user.id = get_jwt_identity()
    if request.method == 'GET':
        payments = Payment.query.all()
        return jsonify([payment.to_dict() for payment in payments]), 201
    
    if request.method == 'POST':
        data = request.get_json()
        invoice_number = data.get('invoice_number')
        payment_method = data.get('payment_method')
        transaction_code = data.get('transaction_code')
        amount_str = data.get('amount')
        payment_date_str = datetime.now().strftime("%Y%m%d")
        
        try:
            amount = Decimal(amount_str)
        except ValueError:
            return jsonify({"Error": "Invalid Format"})

        try:
            payment_date = datetime.strptime(payment_date_str, '%Y%m%d')
        except ValueError:
            return jsonify({"error": "Incorrect date format, should be YYYYMMDD"}), 400

        invoice = Invoice.query.filter_by(invoice_number=invoice_number).first()
        if not invoice:
            return jsonify({"error": "Invoice not found"}), 404

        payment = Payment(
            invoice_number=invoice.invoice_number,
            payment_method=payment_method,
            transaction_code=transaction_code,
            amount=amount,
            payment_date=payment_date
        )
        db.session.add(payment)
        db.session.commit()

        invoice.status = 'paid' if invoice.amount <= amount else 'unpaid'
        db.session.commit()

        return jsonify(payment.to_dict()), 201

@app.route('/customers', methods=['GET', 'POST'])
@jwt_required()
@role_required('Admin')
def get_customers():
    current_user_id = get_jwt_identity()
    
    if request.method == 'GET':
        customers = Customer.query.all()
        return jsonify([customer.to_dict() for customer in customers]), 200
    
    if request.method == 'POST':
        data = request.get_json()
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone_number')

        if not phone_number.startswith('0') and not phone_number.startswith('254'):
            return jsonify({'Error': 'Phone number should start with 0 or 254'}), 400
        
        if phone_number.startswith('0'):
            phone_number = '254' + phone_number[1:]

        if not name or not email:
            return jsonify({"error": "Name and email are required"}), 400

        new_customer = Customer(name=name, email=email, phone_number=phone_number)
        db.session.add(new_customer)
        db.session.commit()
        return jsonify(new_customer.to_dict()), 201

    
@app.route('/invoices/my_invoices', methods=['GET'])
def getIndividualInvoice():
    customer = Customer.query.get(id)
    if not customer:
        return jsonify({'error: customer not found'}), 400

    invoices = Invoice.query.filter_by(customer_name=customer.name).all()
    if not invoices:
        return jsonify({'error: "No invoices found'}), 400
    
    return jsonify([invoice.to_dict() for invoice in invoices]), 200

@app.route('/payments/my_payments', methods=['GET'])
def getIndividualPayments():
    customer = Customer.query.get(id)
    if not customer:
        return jsonify({'error: customer not found'}), 400
    
    payments = Payment.query.filter_by(customer_name=customer.name).all()
    if not payments:
        return jsonify({'error: no payments found'})
    
    return jsonify([payment.to_dict() for payment in payments]), 200


@app.route('/payments/mpesa')
def payMpesa():
    data = {
        "business_shortcode": "174379",
        "passcode": "bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919",
        "phone_number": "254741644151",
        "amount": "1",
        "callback_url": "https://775b-105-163-158-77.ngrok-free.app",
        "description": 'Eripay'
        }
    resp = mpesa_api.MpesaExpress.stk_push(**data)
    return resp

@app.route('/payment/status', methods=['GET'])
def callback_url():
    data = request.get_json()
    result_code = data["Body"]["stkCallback"]["ResultCode"]
    
    #checking the result code
    if result_code != 0:
        error_message = data["Body"]["stkCallback"]["ResultDesc"]
        response_data = {'ResultCode': result_code, 'ResultDesc':error_message}
        return jsonify(response_data)
    
    callback_metadata = data["Body"]["stkCallback"]["CallbackMetadata"]
    amount = None
    phone_number = None
    for item in callback_metadata['item']:
        if item['Name'] == 'Amount':
            amount = item['Value']
        elif item['Name'] == 'PhoneNumber':
            phone_number = item['Value']

    #save the variables [TODO]

    #return a successful response
    response_data = {'ResultCode':result_code, 'ResultDesc':'Success'}
    return jsonify(response_data)

@app.route('/payments/coopbank')
def payCoop():
    reg_data = {
        "shortcode": "",
        "command_id": "CustomerPaybillOnline",
        "amount": "1",
        "msisdn": "254741644151",
        "bill_ref_number": ""    
        }
    transaction = mpesa_api.C2B.simulate(**reg_data)
    #save the variables [TODO]

    return jsonify(transaction)

    
@app.route('/payments/familybank')
def payFamily():
    reg_data = {
        "shortcode": "",
        "command_id": "CustomerPaybillOnline",
        "amount": "1",
        "msisdn": "254741644151",
        "bill_ref_number": ""
        }
    transaction = mpesa_api.C2B.simulate(**reg_data)
    #save the variables[TODO]

    return jsonify(transaction)

@app.route('/confirmation', methods=['POST'])
def c2b_confirmation():
    request_data = request.data

    return jsonify(request_data)


    
print(f"Running in {config_name} mode")
print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI']}")


if __name__ == '__main__':
    app.run(port=80, debug=True)
