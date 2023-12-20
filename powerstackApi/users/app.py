import json
import logging

from utils.utils import *
from functions import * 

# ---------- LOGS ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

# ---------- USERS LAMBDA FUNCTION ----------
def lambda_handler(event, context):
    logger.info(f"event {event}")
    response_body = {"error": "Invalid request"}
    status_code = 400

    if "httpMethod" in event:
        # ---------- SECTION 1: AUTH HEADER ----------
        if 'headers' in event and 'Authorization' in event['headers']:
            id_token = event['headers']['Authorization'].split()[1]

            decoded_token = decode_token(id_token)
            logger.info(decoded_token)
            if decoded_token == "Expired":
                return {
                    "statusCode": 403,
                    "headers": {
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
                        "Content-type": 'application/json'
                    },
                    "body": json.dumps({'error': 'Session expired, log in again'})
                }
     
        try:
            http_method = event["httpMethod"]
            path = event["path"]
            # ---------- SECTION 2: OPTIONS REQUESTS ----------
            if http_method == "OPTIONS":
                return {
                    'statusCode': 200,
                    'headers': {
                        'Access-Control-Allow-Headers': 'Content-Type',
                        'Access-Control-Allow-Origin': '*',
                        'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                    },
                    'body': json.dumps('Options, PASS.')
                }
            # ---------- SECTION 3: GET REQUESTS ----------
            if http_method == "GET":
                if path == "/user/hello":
                    message = "Hello World!"
                
                if path == "/user/dashboard":
                    message = user_check(id_token)
       
                if path == "/user/purchases":
                    message = purchase_history(id_token)

                if path == "/user/receipt" and "queryStringParameters" in event:
                    """
                        Query Param: 'txnRef'
                    """
                    query_params = event['queryStringParameters']
                    message = get_receipt(id_token, query_params=query_params)
                
                if path == "/user/confirmPay" and "queryStringParameters" in event:
                    """
                        Query Param: 'txnRef'
                    """
                    query_params = event['queryStringParameters']
                    message = confirm_pay_with_platform(id_token, query_params=query_params)
 
                logging.info(message)
                status_code = 200
                response_body = {'message': message}

            # ---------- SECTION 4: POST REQUESTS ----------
            if http_method == "POST":
                data = json.loads(event['body'])

                if path == "/user/addMeter":
                    """
                        Body: meterName, meterNumber, meterType, meterLocation
                    """
                    message = add_meter(id_token, data)

                if path == "/user/removeMeter":
                    """
                        Body: meterName, meterNumber, meterType, meterLocation
                    """
                    message = remove_meter(id_token, data)
        
                if path == "/user/ticket":
                    """
                        Body: details
                    """
                    message = submit_ticket(id_token, data)
    
                if path == "/user/initPay":
                    #for both simple and wallet funding transactions
                    message = initialize_pay_with_platform(id_token, data)
    
                if path == "/user/walletPay":
                    message = pay_with_wallet(id_token, data)

                if path =="/user/signUp":
                    """
                        Body: username, password, email, phone_number, user_type
                    """
                    message = user_signup(data)

                if path=="/user/verify":
                    """
                        Body: username, verification_code, password
                    """
                    message = confirm_sign_up(data)
                
                if path=="/user/login":
                    """
                        Body: username, password
                    """
                    message = user_login(data)
                
                if path=="/user/forgotPassword":
                    """
                        Body: username
                    """
                    message = forgot_password_request(data)

                if path=="/user/resetPassword":
                    """
                        Body: username, verification_code, new_password
                    """
                    message = reset_password(data)

                logging.info(message)
                status_code = 200
                response_body = message

        except Exception as e:
            logger.error(f"Unhandled Exception {e}")
            status_code = 400
            response_body = {"error": str(e)}
    else:
        logger.error("httpMethod not present in request.")
        status_code = 400
        response_body = {"error": "httpMethod not present in request."}
    
    response = {
        "statusCode": status_code,
        "headers": {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
            "Content-type": 'application/json'
        },
        "body": json.dumps(response_body, cls=DecimalEncoder)
    }

    return response