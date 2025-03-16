import os
from dotenv import load_dotenv
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_mail import Mail
from flask_apscheduler import APScheduler
from flask_cors import CORS
from .models import db
from flask_jwt_extended import JWTManager

load_dotenv()

mail = Mail()
migrate = Migrate()
admin = Admin(name='Admin Panel', template_mode='bootstrap4')
scheduler = APScheduler()
jwt = JWTManager()

def create_app():
    app = Flask(__name__)
    
    
    CORS(app, resources={
        r"/api/*": {  
            "origins": ["http://localhost:3000", "https://invotrack-frontend.vercel.app"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Range", "X-Content-Range"],
            "supports_credentials": True
        }
    })
    
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.getenv('DEV_DATABASE_URI'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECRET_KEY=os.getenv('SECRET_KEY'),
        MAIL_SERVER=os.getenv('MAIL_SERVER', 'smtp.gmail.com'),
        MAIL_PORT=int(os.getenv('MAIL_PORT', 587)),
        MAIL_USE_TLS=os.getenv('MAIL_USE_TLS', 'true').lower() == 'true',
        MAIL_USERNAME=os.getenv('MAIL_USERNAME'),
        MAIL_PASSWORD=os.getenv('MAIL_PASSWORD'),
        SCHEDULER_API_ENABLED=True,
        CORS_HEADERS='Content-Type'
    )
    
    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    admin.init_app(app)
    scheduler.init_app(app)
    jwt.init_app(app)
    
    
    with app.app_context():
        
        from .user.authentication import user_auth
        from .user.business import business
        from .user.invoices import invoices
        from .user.payments import payments
        from .user.user import user
        from .mpesa import mpesa
        
        app.register_blueprint(user_auth)
        app.register_blueprint(invoices, url_prefix="")
        app.register_blueprint(business, url_prefix="", name="business_route")
        app.register_blueprint(payments, url_prefix="")
        app.register_blueprint(user, url_prefix="")
        app.register_blueprint(mpesa, url_prefix="")
        
        from .scheduler import init_scheduler
        init_scheduler(app)
        
        return app