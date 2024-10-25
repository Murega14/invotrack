# app/__init__.py
import os
from dotenv import load_dotenv
from flask import Flask, render_template, session, jsonify, flash, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_mail import Mail, Message
from flask_apscheduler import APScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from contextlib import contextmanager
from .Routes.authentication import login_is_required
from .views import *
from sqlalchemy import func
from .Routes.authentication import authentication
from .Routes.invoices import invoices
from .Routes.customers import customers
from .Routes.payments import payments
from config import Config


load_dotenv()

db = SQLAlchemy()
mail = Mail()
migrate = Migrate()
admin = Admin(name='Admin Panel', template_mode='bootstrap4')
scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv('SECRET_KEY'),
        MAIL_SERVER=os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
        MAIL_PORT=int(os.getenv('MAIL_PORT', 587)),
        MAIL_USE_TLS=os.getenv('MAIL_USE_TLS', 'true').lower() == 'true',
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
        SCHEDULER_API_ENABLED=True
    )
    
    # Initialize extensions with app
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    admin.init_app(app)
    scheduler.init_app(app)
    
    # Register admin views
    admin.add_view(UserAdmin(User, db.session))
    admin.add_view(ModelView(Customer, db.session))
    admin.add_view(InvoiceAdmin(Invoice, db.session))
    admin.add_view(ModelView(Payment, db.session))
    
    app.register_blueprint(authentication)
    app.register_blueprint(invoices, url_prefix="/invoices")
    app.register_blueprint(customers, url_prefix="/customers")
    app.register_blueprint(payments, url_prefix="/payments")
    
    def update_invoice_status():
        """Update overdue invoices."""
        with app.app_context():
            try:
                now = datetime.now().date()
                overdue_invoices = Invoice.query.filter(
                    Invoice.due_date < now,
                    Invoice.status == 'unpaid'
                ).all()
                
                for invoice in overdue_invoices:
                    invoice.status = 'overdue'
                    
                db.session.commit()
                app.logger.info(f"Updated {len(overdue_invoices)} overdue invoices")
            except Exception as e:
                db.session.rollback()
                app.logger.error(f"Error updating invoice status: {str(e)}")
    
    def send_due_notifications():
        """Send notifications for invoices due soon."""
        with app.app_context():
            try:
                now = datetime.now().date()
                due_invoices = Invoice.query.filter(
                    Invoice.due_date >= now,
                    Invoice.due_date <= now + timedelta(days=3),
                    Invoice.status == 'unpaid'
                ).all()
                
                for invoice in due_invoices:
                    message = Message(
                        subject="Invoice Due Reminder",
                        sender=app.config['MAIL_USERNAME'],
                        recipients=[invoice.user.email]
                    )
                    message.body = f"""
                    Dear {invoice.user.name},
                    
                    This is a reminder that your invoice {invoice.invoice_number} 
                    is due on {invoice.due_date}.
                    
                    Amount Due: ${invoice.amount:,.2f}
                    
                    Please ensure timely payment to avoid late fees.
                    
                    Best regards,
                    Your Business Name
                    """
                    mail.send(message)
                    app.logger.info(f"Sent reminder for invoice {invoice.invoice_number}")
            except Exception as e:
                app.logger.error(f"Error sending notifications: {str(e)}")
    
    # Register scheduled jobs
    scheduler.add_job(
        id='update_overdue_invoices',
        func=update_invoice_status,
        trigger=CronTrigger(hour=0, minute=0),
        replace_existing=True
    )
    
    scheduler.add_job(
        id='send_due_invoice_notifications',
        func=send_due_notifications,
        trigger=CronTrigger(hour=19, minute=30),
        replace_existing=True
    )
    
    # Start the scheduler
    scheduler.start()
    
    # Routes
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
        outstanding_invoices = Invoice.query.filter(
            Invoice.user_id == user.id, 
            Invoice.status != 'paid'
        ).count()
        
        total_paid = db.session.query(func.sum(Invoice.amount))\
            .filter(Invoice.user_id == user.id, Invoice.status == 'paid')\
            .scalar() or 0
            
        total_unpaid = db.session.query(func.sum(Invoice.amount))\
            .filter(Invoice.user_id == user.id, Invoice.status != 'paid')\
            .scalar() or 0
        
        return render_template(
            'dashboard.html',
            outstanding_invoices=outstanding_invoices, 
            total_paid="{:,.2f}".format(total_paid),
            total_unpaid="{:,.2f}".format(total_unpaid),
            user_invoices=user_invoices
        )
    
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('error.html', 
                             error_code=404, 
                             error_message="Page not found"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('error.html', 
                             error_code=500, 
                             error_message="Internal server error"), 500
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)