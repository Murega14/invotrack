import base64
import json
import requests
from datetime import datetime
from app.models import Payment

def generate_access_token():
    consumer_key = ''
    consumer_secret = ''

    url = ''

    try:
        encoded_credentials = base64.b64decode(f'{consumer_key}:{consumer_secret}'.encode())
        headers = {
            'Authorization': f'Basic{encoded_credentials}',
            'Content-Type': 'application/json'
            }
        response = requests.get(url, headers=headers).json()

        if 'access_token' in response:
            return response['access_token']
        else:
            raise Exception("Failed to get access_token" + response['error_description'])
        
    except Exception as e:
        raise Exception("Failed to get access token:" +str(e))
    
def get_short_code(payment_method):
    short_codes = {
        'Mpesa': '',
        'Family Bank': '',
        'Coop Bank': ''

        }
    return short_codes.get(payment_method, '')

def sendStkPush(payment_id):
    token = generate_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

    payment = Payment.query.get(payment_id)
    if not payment:
        raise ValueError(f'Payment with ID {payment_id} not found')
    payment_method = payment.payment_method
    
    shortCode = get_short_code(payment_method)
    

    passkey = ''
    url = ''
    stk_password = base64.b64encode((shortCode + passkey + timestamp).encode('utf-8')).decode('utf-8')

    headers = {
        'Authorization': 'Bearer'+token,
        'Content-Type': 'application/json'
        }
    requestBody = {
        "BusinessShortCode": shortCode,
        "Password": stk_password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPaybillOnline",
        "Amount": 1,
        "PartyA": 254741644151,
        "PartyB": shortCode,
        "PhoneNumber": 254741644151,
        "CallbackURL": '',
        "Transactiondesc": 'Test'
        }
    
    try:
        response = requests.post(url, json=requestBody, headers=headers)
        print(response.json())
        return response.json()
    
    except Exception as e:
        print(f'Error: {str(e)}')