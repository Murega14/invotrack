import os
from dotenv import load_dotenv
from flask import Flask
from app.Routes.authentication import authentication,login_is_required
from app.Routes.invoices import invoices
from .models import db
from config import config
from flask_migrate import Migrate


load_dotenv()

app = Flask(__name__)

config_name = os.getenv('FLASK_CONFIG', 'default')
app.config.from_object(config[config_name])
db.init_app(app)

migrate = Migrate(app, db)

app.secret_key = os.getenv('SECRET_KEY')
app.register_blueprint(authentication, url_prefix="")
app.register_blueprint(invoices, url_prefix="")


@app.route("/")
def index():
    return "Hello World <a href='/login'><button>Login</button></a>"


@app.route("/protected_route")
@login_is_required
def protected_area():
    return f"Hello <br/> <a href='/logout'><button>Logout</button></a>"

if __name__ == "__main__":
    app.run(debug=True)