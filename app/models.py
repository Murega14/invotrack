from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, Enum
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy_serializer import SerializerMixin
from datetime import datetime

metadata = MetaData(naming_convention={
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
})

db = SQLAlchemy(metadata=metadata)

# Database Models
class User(db.Model, SerializerMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(), nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    
    
    oauth_sessions = db.relationship('OAuthSession', backref='user', lazy=True)
    customers = db.relationship('Customer', backref='user', lazy=True)
    invoices = db.relationship('Invoice', backref='user', lazy=True)
    payments = db.relationship('Payment', backref='user', lazy=True)

    serialize_rules = ('-oauth_sessions', '-customers', '-invoices', '-payments')

class OAuthSession(db.Model):
    __tablename__ = 'oauth_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    access_token = db.Column(db.String(200), nullable=False)
    refresh_token = db.Column(db.String(200), nullable=False)
    token_expiry = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def is_token_expired(self):
        return self.token_expiry < datetime.utcnow()
    
    def update_tokens(self, access_token, token_expiry, refresh_token=None):
        self.access_token = access_token
        self.token_expiry = token_expiry
        if refresh_token:
            self.refresh_token = refresh_token
        self.updated_at = datetime.utcnow()
        db.session.commit()

class Customer(db.Model, SerializerMixin):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    
    invoices = db.relationship('Invoice', backref='customer',lazy=True)

    serialize_rules = ('-user', '-invoices')

    def __repr__(self):
        return f'<Customer {self.id}, {self.name}, {self.email}, {self.phone_number}>'

class Invoice(db.Model, SerializerMixin):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    invoice_number = db.Column(db.String(20), nullable=False, unique=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date_issued = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum('unpaid', 'paid', 'overdue', 'partial payment', name='invoice_status'), default='unpaid')
    
    payments = db.relationship('Payment', back_populates='invoice')

    serialize_rules = ('-user', '-payments.invoice', '-customer')

    def __repr__(self):
        return f'<Invoice {self.id}, {self.invoice_number}, {self.amount}, {self.date_issued}, {self.due_date}, {self.status}>'

class Payment(db.Model, SerializerMixin):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)
    payment_method = db.Column(db.Enum('Family Bank', 'Coop Bank', 'Mpesa', name='payment_method'))
    transaction_code = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)

    invoice = db.relationship('Invoice', back_populates='payments')

    serialize_rules = ('-user', '-invoice.payments')

    def __repr__(self):
        return f'<Payment {self.id}, {self.invoice.invoice_number}, {self.payment_method}, {self.transaction_code}, {self.amount}, {self.payment_date}>'
