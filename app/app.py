import os
from dotenv import load_dotenv
from flask import Flask, render_template, session, jsonify, flash, redirect
from app.Routes.authentication import authentication,login_is_required
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


load_dotenv()

app = Flask(__name__)

config_name = os.getenv('FLASK_CONFIG', 'default')
app.config.from_object(config[config_name])
db.init_app(app)

migrate = Migrate(app, db)

app.secret_key = os.getenv('SECRET_KEY')
admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')
app.register_blueprint(authentication, url_prefix="")
app.register_blueprint(invoices, url_prefix="/invoices")
app.register_blueprint(customers, url_prefix="/customers")
app.register_blueprint(payments, url_prefix="/payments")

admin.add_view(UserAdmin(User, db.session))
admin.add_view(ModelView(Customer, db.session))
admin.add_view(InvoiceAdmin(Invoice, db.session))
admin.add_view(ModelView(Payment, db.session))

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/dashboard')
@login_is_required
def dashboard():
    google_id = session.get('google_id')
    
    user = User.query.filter_by(google_id=google_id).first()
    if not user:
        flash('user not found')
        return redirect('/login') 
    user_invoices = Invoice.query.filter_by(user_id=user.id).all()
    
    outstanding_invoices = Invoice.query.filter(Invoice.user_id == user.id, Invoice.status != 'paid').count()
    total_paid = db.session.query(func.sum(Invoice.amount)).filter(Invoice.user_id == user.id, Invoice.status == 'paid').scalar() or 0
    total_unpaid = db.session.query(func.sum(Invoice.amount)).filter(Invoice.user_id == user.id, Invoice.status != 'paid').scalar() or 0
    
    return render_template('dashboard.html',
                           outstanding_invoices=outstanding_invoices, 
                           total_paid="{:,.2f}".format(total_paid),
                           total_unpaid="{:,.2f}".format(total_unpaid),
                           user_invoices=user_invoices)
    

if __name__ == "__main__":
    app.run(debug=True)