import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
from flask import Blueprint, request, jsonify, session, redirect
from .Routes.authentication import login_is_required
from .models import User, Payment, db, Invoice

mpesa = Blueprint('mpesa', __name__)

load_dotenv()

def generate_access_token():
    consumer_key = os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')

    
    encoded_credentials = base64.encode(f'{consumer_key}:{consumer_secret}')
    encoded_credentials_2 = os.getenv('ENCODED_CREDENTIALS')
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate"
    querystring = {"grant_type":"client_credentials"}
    payload = ""
    headers = {
            "Authorization": f"Basic {encoded_credentials}"
        }
    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    return response.text   

@mpesa.route('/<int:invoice_id>/make_payment', methods=['POST'])
@login_is_required
def lipanampesa(invoice_id):
    google_id = session.get('google_id')
    user = User.query.filter_by(google_id=google_id).first()
    
    token = generate_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    shortCode = "174379"
    passkey = os.getenv('PASSKEY')
    url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    stk_password = base64.b64encode((shortCode + passkey + timestamp).encode('utf-8')).decode('utf-8')

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
        }
    
    requestBody = {
        "BusinessShortCode": shortCode,
        "Password": stk_password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerBuyGoodsOnline",
        "Amount": 1,
        "PartyA": 254741644151,
        "PartyB": shortCode,
        "PhoneNumber": 254741644151,
        "CallbackURL": f'https://invotack-2.onrender.com/mpesa/mpesa_callback/{invoice_id}',
        "Transactiondesc": 'Test'
        }
    
    response = requests.post(url, headers=headers, json=requestBody)
    if response.status_code == 200:
        response_data = response.get_json()
        return redirect(f'/mpesa_callback/{invoice_id}')
    else:
        return jsonify({'error': 'Failed to initiate STK push', 'status_code': response.status_code, 'details': response.text}), 400
    
@mpesa.route('/mpesa_callback/<int:invoice_id>', methods=['POST'])
def callback(invoice_id):
    callback_data = request.json()
    google_id = session.get('google_id')
    user = User.query.filter_by(google_id=google_id).first()
    invoice = Invoice.query.filter_by(id=invoice_id).first()
    
    #check the result code
    result_code = callback_data['Body']['StkCallback']['ResultCode']
    
    if result_code != 0:
        error_message = callback_data['Body']['stkCallback']['ResultDesc']
        response_data = {
            'ResultCode': result_code,
            'ResultDesc': error_message
        }
        return jsonify(response_data)
    
    callback_metadata = callback_data['Body']['stkCallback']['CallbackMetadata']
    amount = None
    transaction_code = None
    
    for item in callback_metadata['item']:
        if item['Name'] == 'Amount':
            amount = item['Value']
        elif item['Name'] == 'MpesaReceiptNumber':
            transaction_code = item['Value']
            
    # save the variables in the database
    new_payment = Payment(user_id=user.id,
                          invoice_number=invoice.invoice_number,
                          amount=amount,
                          transaction_code=transaction_code,
                          payment_method="Mpesa",
                          payment_date=datetime.now().strftime('%Y%m%d%H%M%S'))
    db.session.add(new_payment)
    db.session.commit()
    
    #return a sucess response to the server
    response_data = {
        'ResultCode': result_code,
        'ResultDesc': 'Success'
    }
    
    return redirect('/')
    