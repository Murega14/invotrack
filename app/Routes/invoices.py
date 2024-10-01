from flask import Blueprint, request
from authentication import login_is_required
import jsonify
from app.models import Invoice, db

invoice = Blueprint("invoice", __name__)

@invoice.route('/invoices', methods=['GET'])
@login_is_required
def invoices():
    