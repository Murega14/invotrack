import os
from dotenv import load_dotenv
from flask import Flask
from app.Routes.authentication import authentication,login_is_required
from app.Routes.invoices import invoices
from app.Routes.customers import customers
from .models import *
from config import config
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from .views import InvoiceAdmin, UserAdmin


load_dotenv()

app = Flask(__name__)

config_name = os.getenv('FLASK_CONFIG', 'default')
app.config.from_object(config[config_name])
db.init_app(app)

migrate = Migrate(app, db)

app.secret_key = os.getenv('SECRET_KEY')
admin = Admin(app, name='Admin Panel', template_mode='bootstrap4')
app.register_blueprint(authentication, url_prefix="")
app.register_blueprint(invoices, url_prefix="")
app.register_blueprint(customers, url_prefix="")
admin.add_view(UserAdmin(User, db.session))
admin.add_view(ModelView(Customer, db.session))
admin.add_view(InvoiceAdmin(Invoice, db.session))
admin.add_view(ModelView(Payment, db.session))

@app.route("/")
def index():
    return "Hello World <a href='/login'><button>Login</button></a>"


@app.route("/protected_route")
@login_is_required
def protected_area():
    return f"Hello <br/> <a href='/logout'><button>Logout</button></a>"

if __name__ == "__main__":
    app.run(debug=True)