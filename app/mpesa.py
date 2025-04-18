import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
import logging
from flask import Blueprint, request, jsonify, session, redirect
from .models import User, Payment, db, Invoice

mpesa = Blueprint('mpesa', __name__)

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def generate_access_token():
    """
    generates an access token for api authentication

    Returns:
        _Response in a json format
    """
    consumer_key = os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')
    
    credentials = f'{consumer_key}:{consumer_secret}'
    encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate"
    querystring = {"grant_type":"client_credentials"}
    headers = {
        "Authorization": f"Basic {encoded_credentials}"
    }
    
    response = requests.request("GET", url, headers=headers, params=querystring)
    return response.json()

@mpesa.route('/<int:invoice_id>/make_payment', methods=['POST'])
def lipa_na_mpesa(id: int):
    """
    initializes an stk push for invoice payment

    Args:
        id (int): invoice identifier

    Returns:
        redirects to the callback url
    """
    google_id = session.get('google_id')
    user = User.query.get_or_404(google_id)
    invoice = Invoice.query.get_or_404(id)
    
    response = generate_access_token()
    token = response.get('access_token')
    if not token:
        logger(f"access token not found: {response}")
        return jsonify({"error": "no token for authorization"}), 403
    
    timestamp = datetime.now().strftime('%H%M%S %Y%m%d')
    short_code = "174379"
    passkey = os.getenv('PASSKEY')
    
    url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    stk_password = base64.b64encode((short_code + passkey + timestamp).encode('utf-8')).decode('utf-8')
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    request_body = {
        "BusinessShortCode": short_code,
        "Password": stk_password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerBuyGoodsOnline",
        "Amount": int(invoice.amount),
        "PartyA": 254741644151, #change to invoice.customer.phone_number
        "PartyB": short_code,
        "PhoneNumber": 254741644151, #change to invoice.customer.phone_number
        "CallbackURL": f"https://invotack-2.onrender.com/mpesa/mpesa_callback/{id}",
        "TransactionDesc": f'Payment for Invoice #{invoice.invoice_number}'        
    }
    
    response = requests.post(url, headers=headers, json=request_body)
    
    if response.status_code == 200:
        return redirect('/mpesa_callback/<int:invoice_id>')
    else:
        return jsonify({
            "error": "failed to initialize stk push",
            "status_code": response.status_code,
            "details": response.text
        }), 400
        

@mpesa.route('/mpesa_callback/<int:invoice_id>', methods=['POST'])
def callback(invoice_id):
    try:
        callback_data = request.get_json()
        google_id = session.get('google_id')
        user = User.query.filter_by(google_id=google_id).first()
        invoice = Invoice.query.get_or_404(invoice_id)
        
        result_code = callback_data['Body']['stkCallback']['ResultCode']
        
        if result_code != 0:
            error_message = callback_data['Body']['stkCallback']['ResultDesc']
            return jsonify({
                'ResultCode': result_code,
                'ResultDesc': error_message
            }), 400
        
        callback_metadata = callback_data['Body']['stkCallback']['CallbackMetadata']['Item']
        amount = next((item['Value'] for item in callback_metadata if item['Name'] == 'Amount'), None)
        transaction_code = next((item['Value'] for item in callback_metadata if item['Name'] == 'MpesaReceiptNumber'), None)
        
        if amount and transaction_code:
            new_payment = Payment(
                user_id=user.id,
                invoice_id=invoice_id,
                amount=amount,
                transaction_code=transaction_code,
                payment_method="Mpesa",
                payment_date=datetime.now()
            )
            db.session.add(new_payment)
            invoice.status = 'paid'
            db.session.commit()
            
            return jsonify({
                'ResultCode': 0,
                'ResultDesc': 'Success'
            })
            
    except Exception as e:
        return jsonify({
            'ResultCode': 1,
            'ResultDesc': f'Error: {str(e)}'
        }), 500
