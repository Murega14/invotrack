import base64
import json
import requests
from datetime import datetime
from app.models import Payment

def generate_access_token():
    consumer_key = ''
    consumer_secret = ''

    
    encoded_credentials = base64.b64decode(f'{consumer_key}:{consumer_secret}'.encode())
    
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate"
    querystring = {"grant_type":"client_credentials"}
    payload = ""
    headers = {
            "Authorization": "Basic {encoded_credentials}"
        }
    response = requests.request("GET", url, data=payload, headers=headers, params=querystring)
    return response.text   


def sendStkPush():
    token = generate_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    shortCode = "9276285"
    passkey = 'bfb279f9aa9bdbcf158e97dd71a467cd2e0c893059b10f78e6b72ada1ed2c919'
    url = 'https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest'
    stk_password = base64.b64encode((shortCode + passkey + timestamp).encode('utf-8')).decode('utf-8')

    headers = {
        'Authorization': 'Bearer'+token,
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
        "CallbackURL": '',
        "Transactiondesc": 'Test'
        }
    
    try:
        response = requests.post(url, json=requestBody, headers=headers)
        print(response.json())
        return response.json()
    
    except Exception as e:
        print(f'Error: {str(e)}')

def sendStkPush_familyBank():
    token = generate_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    shortCode = '222111'
    passkey = ''
    url = ''
    stk_password = base64.b64decode((shortCode + passkey + timestamp).encode('utf-8')).decode('utf-8')

    headers = {
        'Content-Type': 'application/json'
        }
    
    requestBody = {
        "BusinessShortCode": shortCode,
        "BillRefNumber": '752292',
        "TransactionType": "CustomerPaybillonline",

        }