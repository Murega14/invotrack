import os
from dotenv import load_dotenv
from flask import Flask, render_template, session, jsonify, flash, redirect
from app.Routes.authentication import authentication, login_is_required
from app.Routes.invoices import invoices
from app.Routes.customers import customers
from .Routes.payments import payments
from .models import *
from config import config
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from .views import InvoiceAdmin, UserAdmin
from .templates import *
from sqlalchemy import func
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)

# Load configuration
config_name = os.getenv('FLASK_CONFIG', 'default')
app.config.from_object(config[config_name])
db.init_app(app)
mail = Mail(app)
scheduler = APScheduler()

migrate = Migrate(app, db)

app.secret_key = os.getenv('SECRET_KEY')
admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')

# Register blueprints
app.register_blueprint(authentication, url_prefix="")
app.register_blueprint(invoices, url_prefix="/invoices")
app.register_blueprint(customers, url_prefix="/customers")
app.register_blueprint(payments, url_prefix="/payments")

# Flask-Admin Views
admin.add_view(UserAdmin(User, db.session))
admin.add_view(ModelView(Customer, db.session))
admin.add_view(InvoiceAdmin(Invoice, db.session))
admin.add_view(ModelView(Payment, db.session))

# Configure the scheduler before initialization
app.config['SCHEDULER_API_ENABLED'] = True
scheduler.init_app(app)
scheduler.start()

def update_invoice_status():
    """Update invoices that are overdue."""
    with app.app_context():
        now = datetime.now().date()
        overdue_invoices = Invoice.query.filter(
            Invoice.due_date < now,
            Invoice.status == 'unpaid'
        ).all()
        
        for invoice in overdue_invoices:
            invoice.status = 'overdue'
            
        db.session.commit()

scheduler.add_job(
    func=update_invoice_status,
    trigger=IntervalTrigger(days=1),
    id='update_overdue_invoices',
    replace_existing=True
)

def send_due_notifications():
    """Send notifications for invoices due within the next three days."""
    with app.app_context():
        now = datetime.now().date()
        due_invoices = Invoice.query.filter(
            Invoice.due_date >= now,
            Invoice.due_date <= now + timedelta(days=3),
            Invoice.status == 'unpaid'
        ).all()
        
        for invoice in due_invoices:
            send_invoice_email(invoice)

def send_invoice_email(invoice):
    """Send an email reminder for the given invoice."""
    message = Message(
        subject="Invoice Due Reminder",
        sender=os.getenv('MAIL_USERNAME'),
        recipients=[invoice.user.email]
    )
    message.body = f"Dear {invoice.user.name}, your invoice {invoice.invoice_number} is due on {invoice.due_date}."
    mail.send(message=message)

scheduler.add_job(
    func=send_due_notifications,
    trigger=IntervalTrigger(days=1),
    id='send_due_invoice_notifications',
    replace_existing=True
)

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/dashboard')
@login_is_required
def dashboard():
    google_id = session.get('google_id')
    
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        flash('User not found')
        return redirect('/login') 
    user_invoices = Invoice.query.filter_by(user_id=user.id).all()
    
    outstanding_invoices = Invoice.query.filter(Invoice.user_id == user.id, Invoice.status != 'paid').count()
    total_paid = db.session.query(func.sum(Invoice.amount)).filter(Invoice.user_id == user.id, Invoice.status == 'paid').scalar() or 0
    total_unpaid = db.session.query(func.sum(Invoice.amount)).filter(Invoice.user_id == user.id, Invoice.status != 'paid').scalar() or 0
    
    return render_template(
        'dashboard.html',
        outstanding_invoices=outstanding_invoices, 
        total_paid="{:,.2f}".format(total_paid),
        total_unpaid="{:,.2f}".format(total_unpaid),
        user_invoices=user_invoices
    )

if __name__ == "__main__":
    app.run(debug=True)
