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


load_dotenv()

# Initialize extensions
db = SQLAlchemy()
mail = Mail()
migrate = Migrate()
admin = Admin(name='Admin Panel', template_mode='bootstrap4')

class Config:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "UTC"
    MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.getenv('SECRET_KEY')

class SchedulerService:
    def __init__(self, app=None, db=None, mail=None):
        self.scheduler = APScheduler()
        self.db = db
        self.mail = mail
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        app.config.from_object(Config)
        self.scheduler.init_app(app)
        self.app = app
        
        # Register jobs
        self.register_jobs()
        
        # Start scheduler
        self.scheduler.start()
    
    @contextmanager
    def app_context(self):
        """Context manager to handle app context"""
        with self.app.app_context():
            try:
                yield
            except Exception as e:
                self.app.logger.error(f"Scheduler error: {str(e)}")
                if self.db:
                    self.db.session.rollback()
            finally:
                if self.db:
                    self.db.session.close()
    
    def update_invoice_status(self):
        """Update overdue invoices - runs daily at midnight"""
        with self.app_context():
            now = datetime.now().date()
            try:
                overdue_invoices = Invoice.query.filter(
                    Invoice.due_date < now,
                    Invoice.status == 'unpaid'
                ).all()
                
                for invoice in overdue_invoices:
                    invoice.status = 'overdue'
                    self.app.logger.info(f"Updated invoice {invoice.invoice_number} to overdue")
                
                self.db.session.commit()
            except Exception as e:
                self.app.logger.error(f"Failed to update invoice status: {str(e)}")
                raise
    
    def send_due_notifications(self):
        """Send notifications for upcoming due invoices - runs daily at 9 AM"""
        with self.app_context():
            now = datetime.now().date()
            try:
                due_invoices = Invoice.query.filter(
                    Invoice.due_date >= now,
                    Invoice.due_date <= now + timedelta(days=3),
                    Invoice.status == 'unpaid'
                ).all()
                
                for invoice in due_invoices:
                    self.send_invoice_email(invoice)
                    self.app.logger.info(f"Sent reminder for invoice {invoice.invoice_number}")
            except Exception as e:
                self.app.logger.error(f"Failed to send notifications: {str(e)}")
                raise
    
    def send_invoice_email(self, invoice):
        """Helper method to send individual invoice emails"""
        try:
            message = Message(
                subject="Invoice Due Reminder",
                sender=self.app.config['MAIL_USERNAME'],
                recipients=[invoice.user.email]
            )
            message.body = f"""
            Dear {invoice.user.name},
            
            This is a reminder that your invoice {invoice.invoice_number} is due on {invoice.due_date}.
            
            Amount Due: ${invoice.amount:,.2f}
            
            Please ensure timely payment to avoid late fees.
            
            Best regards,
            Your Business Name
            """
            self.mail.send(message)
        except Exception as e:
            self.app.logger.error(f"Failed to send email for invoice {invoice.invoice_number}: {str(e)}")
            raise
    
    def register_jobs(self):
        """Register all scheduled jobs"""
        # Update overdue invoices at midnight
        self.scheduler.add_job(
            id='update_overdue_invoices',
            func=self.update_invoice_status,
            trigger=CronTrigger(hour=19, minute=0),
            replace_existing=True
        )
        
        # Send notifications at 9 AM
        self.scheduler.add_job(
            id='send_due_invoice_notifications',
            func=self.send_due_notifications,
            trigger=CronTrigger(hour=19, minute=0),
            replace_existing=True
        )

def create_app(config_name=None):
    app = Flask(__name__)
    
    #configuration
    if config_name is None:
        config_name = os.getenv('FLASK_CONFIG', 'default')
    app.config.from_object(Config)
    
    #extensions
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    admin.init_app(app)
    
    # Initialize scheduler
    scheduler_service = SchedulerService(app, db, mail)
    
    #blueprints
    app.register_blueprint(authentication, url_prefix="")
    app.register_blueprint(invoices, url_prefix="/invoices")
    app.register_blueprint(customers, url_prefix="/customers")
    app.register_blueprint(payments, url_prefix="/payments")
    
    #admin views 
    admin.add_view(UserAdmin(User, db.session))
    admin.add_view(ModelView(Customer, db.session))
    admin.add_view(InvoiceAdmin(Invoice, db.session))
    admin.add_view(ModelView(Payment, db.session))
    
    #routes
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
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500
    
    return app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)