from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, Enum
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy_serializer import SerializerMixin


metadata = MetaData(naming_convention={
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
})

db = SQLAlchemy(metadata=metadata)

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    
    oauth_sessions = db.relationship('OAuthSession', backref='user', lazy=True)
    
class OAuthSession(db.Model):
    __tablename__ = 'oauthsession'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    access_token = db.Column(db.String(200), nullable=False)
    refresh_token = db.Column(db.String(200), nullable=False)
    token_expiry = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    
    def is_token_expired(self):
        return self.token_expiry < db.func.current_timestamp()
    
    def update_tokens(self, access_token, token_expiry, refresh_token=None):
        self.access_token = access_token
        self.token_expiry = token_expiry
        if refresh_token:
            self.refresh_token = refresh_token
        db.session.commit()
        

class Customer(db.Model, SerializerMixin):
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone_number = db.Column(db.Integer, nullable=False, unique=True)

    invoices = db.relationship('Invoice', back_populates='customer')
    users = db.relationship('User', backref='customers')
    serialize_rules = ('-invoices.customer', '-payments.customer',)

    def __repr__(self):
        return f'<Customer {self.id}, {self.name}, {self.email}, {self.phone_number}>'


class Invoice(db.Model, SerializerMixin):
    __tablename__ = 'invoices'

    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.Integer, nullable=False, unique=True)
    customer_name = db.Column(db.Integer, db.ForeignKey('customers.name'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    date_issued = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum('unpaid', 'paid', 'overdue', 'partial payment', name='invoice_status'), default='unpaid')
    
    customer = db.relationship('Customer', back_populates='invoices')
    payments = db.relationship('Payment', back_populates='invoice')
    users = db.relationship('User', backref='invoices')

    serialize_rules = ('-payments.invoice', '-customers.invoice',)

    def __repr__(self):
        return f'<Invoice {self.id}, {self.invoice_number}, {self.customer_name}, {self.amount}, {self.date_issued}, {self.due_date}, {self.status}>'

class Payment(db.Model, SerializerMixin):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invoice_number = db.Column(db.Integer, db.ForeignKey('invoices.invoice_number'), nullable=False)
    payment_method = db.Column(db.Enum('Family Bank', 'Coop Bank', 'Mpesa', name='payment_method'))
    transaction_code = db.Column(db.String, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.DateTime, default=db.func.current_timestamp())

    invoice = db.relationship('Invoice', back_populates='payments')
    user = db.relationship('User', backref='payments')
    serialize_rules = ('-invoices.payment', '-customers.payment',)

    def __repr__(self):
        return f'<Payment {self.id}, {self.invoice_number}, {self.payment_method}, {self.transaction_code}, {self.amount}, {self.payment_date}>'
