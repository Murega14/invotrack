from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import Enum, Numeric, ForeignKey, func
import uuid

# Initialize SQLAlchemy
db = SQLAlchemy()

class BaseModel():
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = db.Column(db.DateTime, default=func.now())
    updated_at = db.Column(db.DateTime, default=None, onupdate=func.now())

class User(db.Model, BaseModel):
    __tablename__ = 'users'
    
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    
    businesses = db.relationship('Business', backref='owner', lazy=True)
    invoices_issued = db.relationship('Invoice', backref='issuer', lazy=True)
    payments = db.relationship('Payment', backref='payer', lazy=True)
    transactions = db.relationship('TransactionHistory', backref='user', lazy=True)

class Business(db.Model, BaseModel):
    __tablename__ = 'businesses'
    
    owner_id = db.Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(255), unique=True, nullable=False)
    phone_number = db.Column(db.String(10), nullable=False)
    email = db.Column(db.String(), nullable=False)
    
    invoices = db.relationship('Invoice', backref='recipient_business', lazy=True)

class Invoice(db.Model, BaseModel):
    __tablename__ = 'invoices'
    
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    issuer_id = db.Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    business_id = db.Column(UUID(as_uuid=True), ForeignKey('businesses.id'), nullable=False)
    status = db.Column(Enum('pending', 'overdue', 'cancelled', 'paid', name='invoice_status'), default='pending')
    total_amount = db.Column(Numeric(10, 2), nullable=False)
    date_issued = db.Column(db.DateTime, default=func.now())
    due_date = db.Column(db.DateTime, nullable=False)
    
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='invoice', lazy=True)

class InvoiceItem(db.Model, BaseModel):
    __tablename__ = 'invoice_items'
    
    invoice_id = db.Column(UUID(as_uuid=True), ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False)
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(Numeric(10, 2), nullable=False)
    subtotal = db.Column(Numeric(10, 2), nullable=False)
    
class Payment(db.Model, BaseModel):
    __tablename__ = 'payments'
    
    invoice_id = db.Column(UUID(as_uuid=True), ForeignKey('invoices.id', ondelete='CASCADE'), nullable=False)
    payer_id = db.Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    payment_method = db.Column(Enum('credit_card', 'bank_transfer', 'paypal', 'mpesa', name='payment_methods'))
    transaction_code = db.Column(db.String(255), unique=True, nullable=False)
    amount = db.Column(Numeric(10, 2), nullable=False)
    payment_date = db.Column(db.DateTime, default=func.now())
    status = db.Column(Enum('successful', 'failed', 'pending', name='payment_status'), default='successful')
    
    transactions = db.relationship('TransactionHistory', backref='payment', lazy=True)

class TransactionHistory(db.Model, BaseModel):
    __tablename__ = 'transaction_history'
    
    user_id = db.Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    invoice_id = db.Column(UUID(as_uuid=True), ForeignKey('invoices.id'), nullable=True)
    payment_id = db.Column(UUID(as_uuid=True), ForeignKey('payments.id'), nullable=True)
    action = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=func.now())
