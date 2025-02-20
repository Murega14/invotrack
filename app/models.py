from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.dialects.postgresql import ENUM

metadata = MetaData(naming_convention={
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
})

db = SQLAlchemy(metadata=metadata)

invoice_status_enum = ENUM(
    'pending',
    'overdue',
    'paid',
    'cancelled',
    name='invoice_status_enum',
    create_type=True
)

class User(db.Model, SerializerMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(), unique=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(), nullable=False)
    
    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_hash(self, password):
        return check_password_hash(self.password_hash, password)
        
    customers = db.relationship('Customer', back_populates="user", cascade="all, delete-orphan", lazy=True)
    invoices = db.relationship('Invoice', back_populates="user", cascade="all, delete-orphan", lazy=True)
    payments = db.relationship('Payment', back_populates="user", cascade="all, delete-orphan", lazy=True)

    serialize_rules = ('-customers', '-invoices', '-payments')
    
class Business(db.Model, SerializerMixin):
    __tablename__ = 'business'
    
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(), unique=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String())
    
    def hash_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_hash(self, password):
        return check_password_hash(self.password_hash, password)
        
    customers = db.relationship('Customer', back_populates="business", cascade="all, delete-orphan", lazy=True)
    invoices = db.relationship('Invoice', back_populates="business", cascade="all, delete-orphan", lazy=True)
    payments = db.relationship('Payment', back_populates="business", cascade="all, delete-orphan", lazy=True)

    serialize_rules = ('-customers', '-invoices', '-payments')

class Customer(db.Model, SerializerMixin):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    
    user = db.relationship('User', back_populates="customers")
    business = db.relationship('Business', back_populates="customers")
    invoices = db.relationship('Invoice', back_populates="customer", cascade="all, delete-orphan", lazy=True)
    payments = db.relationship('Payment', back_populates="customer", cascade="all, delete-orphan", lazy=True)

    serialize_rules = ('-invoices', '-payments')

class Invoice(db.Model, SerializerMixin):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    amount = db.Column(db.Integer, nullable=False)
    date_issued = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(invoice_status_enum, default='pending', nullable=False)
    
    user = db.relationship('User', back_populates="invoices")
    business = db.relationship('Business', back_populates="invoices")
    customer = db.relationship('Customer', back_populates="invoices")
    details = db.relationship('InvoiceDetail', back_populates="invoice", cascade="all, delete-orphan", lazy=True)
    payments = db.relationship('Payment', backref="invoice", cascade="all, delete-orphan", lazy=True)

class Payment(db.Model, SerializerMixin):
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    business_id = db.Column(db.Integer, db.ForeignKey('business.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    date_paid = db.Column(db.Date, nullable=False)

    user = db.relationship('User', back_populates="payments")
    business = db.relationship('Business', back_populates="payments")
    customer = db.relationship('Customer', back_populates="payments")

    serialize_rules = ('-invoice', '-user', '-business', '-customer')

class InvoiceDetail(db.Model):
    __tablename__ = 'invoice_details'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    services = db.Column(db.String(), nullable=False)
    sub_total = db.Column(db.Integer, nullable=False)
    
    invoice = db.relationship('Invoice', back_populates="details")