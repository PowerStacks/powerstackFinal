import logging
import requests
import json

from utils.exception_handler import *

"""
    - Functions needed:
        1. Payment with payment platform - Flutterwave and Zainpay - to init payment
        2. Callback function to confirm payment with platform, called once first function is done running from UI
            - Will: add txnRef as queryParam to confirm payment
                    vend electricity to user if user is doing a simply payment
                    will fund wallet and return new wallet info / receipt
                    return receipt (maybe handle this on functions.py
        3. Pay with wallet


        ** Payment types: SIMPLE (directly through payment platform / restricted to reg users), 
                          R-WALLET (regular user - wallet payment), 
                          R-FUND
                          M-FUND
                          M-WALLET (merchant - wallet, ie commission is involved), 
        ** Depending on selected payment platform use specific gloabl configs
    """

# ---------- LOGS ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------- GLOBALS ----------
FLUTTERWAVE_KEY = 'FLWPUBK_TEST-635b3e8a893d30ade9af302c854004b7-X'
FLUTTERWAVE_SECRET_KEY = 'FLWSECK_TEST-73b65f61590836d70222e7720ec3a360-X'
FLW_URL = 'https://api.flutterwave.com/v3/charges?type=bank_transfer'

PAYSTACK_SECRET_KEY = 'sk_test_f87d18897addafe7af206da9192c1111c1163b2a'
PST_INIT_URL = 'https://api.paystack.co/transaction/initialize'
PST_CONFIRM_URL = 'https://api.paystack.co/transaction/verify/'

# ---------- SECTION 1: FLUTTERWAVE ----------
# Charges a 1.4% flat fee
def flutterwave_init_payment(email, amount, tx_ref):
    header = {
        'Authorization': f'Bearer: {FLUTTERWAVE_SECRET_KEY}',
        'content-type': 'application/json'
        }
    data = {
        "tx_ref": tx_ref,
        "amount": amount,
        "email": email,
        "currency": "NGN"
    }
    try:
        response = requests.post(FLW_URL,data,header)
        return f'{response}'
    except Exception as e:
        error_format(e)


    
#def confirm_payment():

#def wallet_pay():

# ---------- SECTION 2: PAYSTACK ----------
# Paystack Charges 1.5% on each transaction + 100 ( over 2500 )
def paystack_init_payment(email, amount, tx_ref, metadata):
    headers = {
        'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
        'content-type': 'application/json'
        }
    
    data = {
        "reference": tx_ref,
        "amount": amount, # in kobo
        "email": email,
        "metadata": json.dumps(metadata)
    }

    try:
        response = requests.post(PST_INIT_URL,data=json.dumps(data),headers=headers).json()
        logger.info(response)
        return {
            'authorization_url': response.get('data').get('authorization_url'),
            'txnRef': response.get('data').get('reference')
            }
    except Exception as e:
        error_format(e)
    
def paystack_confirm_payment(tx_ref):
    try:
        headers = {
            'Authorization': f'Bearer {PAYSTACK_SECRET_KEY}',
            'content-type': 'application/json'
            }
        
        
        response = requests.get(PST_CONFIRM_URL + tx_ref, headers=headers).json()
        return response
    except Exception as e:
        error_format(e)

    
# ---------- SECTION 3: ZAINPAY ----------

# ---------- SECTION 3: VENDING ( handle prepaid / postpaid here? ) ----------
#def vend_electricity():