import base64
import requests
from datetime import datetime
from dotenv import load_dotenv
import os
from flask import Blueprint, request, jsonify, session, redirect
from .Routes.authentication import login_is_required
from .models import User, Payment, Invoice

mpesa = Blueprint('mpesa', __name__)

load_dotenv()

def generate_access_token():
    consumer_key = os.getenv('CONSUMER_KEY')
    consumer_secret = os.getenv('CONSUMER_SECRET')

    
    encoded_credentials = base64.b64decode(f'{consumer_key}:{consumer_secret}'.encode())
    
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate"
    querystring = {"grant_type":"client_credentials"}
    payload = ""
    headers = {
            "Authorization": f"Basic {encoded_credentials}"
        }
    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    return response.text   

@mpesa.route('/make_payment')
@login_is_required
def lipanampesa():
    google_id = session.get('google_id')
    user = User.query.filter_by(google_id=google_id).first()
    
    token = generate_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    shortCode = "9276285"
    passkey = os.getenv('PASSKEY')
    url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    stk_password = base64.b64encode((shortCode + passkey + timestamp).encode('utf-8')).decode('utf-8')

    headers = {
        'Authorization': 'Bearer' + token,
        'Content-Type': 'application/json'
        }
    
    requestBody = {
        "BusinessShortCode": shortCode,
        "Password": stk_password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerBuyGoodsOnline",
        "Amount": 1,
        "PartyA": user.Customer.phone_number,
        "PartyB": shortCode,
        "PhoneNumber": user.Customer.phone_number,
        "CallbackURL": 'https://invotack-2.onrender.com/mpesa/mpesa_callback',
        "Transactiondesc": 'Test'
        }
    
    return redirect('mpesa_callback')
    
@mpesa.route('mpesa_callback', methods=['POST'])
def callback():
    callback_data = request.json()
    
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
    #TODO
    
    #return a sucess response to the server
    response_data = {
        'ResultCode': result_code,
        'ResultDesc': 'Success'
    }
    
    return jsonify(response_data)
    