from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, Enum
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

metadata = MetaData(naming_convention={
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
})

db = SQLAlchemy(metadata=metadata)

# Database Models
class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False, unique=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(128), nullable=False)

    roles = db.relationship('Role', secondary='user_roles')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    
    def __repr__(self):
        return f'<Customer {self.id}, {self.username}, {self.name}, {self.email}>'

class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

class UserRoles(db.Model):
    __tablename__ = 'user_roles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id', ondelete='CASCADE'))

class Customer(db.Model, SerializerMixin):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)

    invoices = db.relationship('Invoice', back_populates='customer')

    serialize_rules = ('-invoices.customer', '-payments.customer',)

    def __repr__(self):
        return f'<Customer {self.id}, {self.name}, {self.email}>'


class Invoice(db.Model, SerializerMixin):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.Integer, db.ForeignKey('customers.name'), nullable=False)
    invoice_number = db.Column(db.Integer, nullable=False, unique=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date_issued = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum('unpaid', 'paid', name='invoice_status'), default='unpaid')
    
    customer = db.relationship('Customer', back_populates='invoices')
    payments = db.relationship('Payment', back_populates='invoice')

    serialize_rules = ('-payments.invoice', '-customers.invoice',)

    def __repr__(self):
        return f'<Invoice {self.id}, {self.invoice_number}, {self.customer_name}, {self.amount}, {self.status}>'

class Payment(db.Model, SerializerMixin):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.Integer, db.ForeignKey('invoices.invoice_number'), nullable=False)
    payment_method = db.Column(db.Enum('Family Bank', 'Coop Bank', 'Mpesa', name='payment_method'))
    transaction_code = db.Column(db.String, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.DateTime, default=db.func.current_timestamp())

    invoice = db.relationship('Invoice', back_populates='payments')

    serialize_rules = ('-invoices.payment', '-customers.payment',)

    def __repr__(self):
        return f'<Payment {self.id}, {self.invoice_number}, {self.payment_method}, {self.transaction_code}, {self.amount}, {self.payment_date}>'
