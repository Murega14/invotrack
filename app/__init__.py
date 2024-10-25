import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_mail import Mail
from flask_apscheduler import APScheduler
from .models import db

load_dotenv()

mail = Mail()
migrate = Migrate()
admin = Admin(name='Admin Panel', template_mode='bootstrap4')
scheduler = APScheduler()

def create_app():
    app = Flask(__name__)
    
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv('DEV_DATABASE_URI'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv('SECRET_KEY'),
        MAIL_SERVER=os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
        MAIL_PORT=int(os.getenv('MAIL_PORT', 587)),
        MAIL_USE_TLS=os.getenv('MAIL_USE_TLS', 'true').lower() == 'true',
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
        SCHEDULER_API_ENABLED=True
    )
    
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    admin.init_app(app)
    scheduler.init_app(app)
    
    with app.app_context():
        from .models import User, Customer, Invoice, Payment
        from .views import InvoiceAdmin, UserAdmin
        from flask_admin.contrib.sqla import ModelView
        
        admin.add_view(UserAdmin(User, db.session))
        admin.add_view(ModelView(Customer, db.session))
        admin.add_view(InvoiceAdmin(Invoice, db.session))
        admin.add_view(ModelView(Payment, db.session))
        
        from .Routes.authentication import authentication
        from .Routes.invoices import invoices
        from .Routes.customers import customers
        from .Routes.payments import payments
        
        app.register_blueprint(authentication)
        app.register_blueprint(invoices, url_prefix="/invoices")
        app.register_blueprint(customers, url_prefix="/customers")
        app.register_blueprint(payments, url_prefix="/payments")
        
        from .scheduler import init_scheduler
        init_scheduler(app)
        
        return app