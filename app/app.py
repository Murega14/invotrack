import os
from dotenv import load_dotenv
from flask import Flask
from app.Routes.authentication import authentication,login_is_required
from app.Routes.invoices import invoice

load_dotenv()

app = Flask(__name__)
app.secret_key = "teddy"
app.register_blueprint(authentication, url_prefix="")
app.register_blueprint(invoice, url_prefix="")

@app.route("/")
def index():
    return "Hello World <a href='/login'><button>Login</button></a>"


@app.route("/protected_area")
@login_is_required
def protected_area():
    return f"Hello <br/> <a href='/logout'><button>Logout</button></a>"

if __name__ == "__main__":
    app.run()