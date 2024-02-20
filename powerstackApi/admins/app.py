import json
import logging
from decimal import Decimal

from functions import * 
from analytics import *
from transfers import *
from utils.general_utils import *
from utils.exception_handler import *


# ---------- LOGS ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
    
# ---------- ADMIN LAMBDA FUNCTION ----------
def lambda_handler(event, context):
    logger.info(f"event {event}")
    response_body = {"error": "Invalid request"}
    status_code = 400

    if "httpMethod" in event:
        try:
            http_method = event["httpMethod"]
            path = event["path"]

            # ---------- SECTION 1: AUTH HEADER ----------
            if 'headers' in event and 'Authorization' in event['headers']:
                id_token = event['headers']['Authorization'].split()[1]

                decoded_token = decode_token(id_token)
                if decoded_token == "Expired":
                    return {
                        "statusCode": 403,
                        "headers": {
                            'Access-Control-Allow-Headers': 'Content-Type',
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
                            "Content-type": 'application/json'
                        },
                        "body": json.dumps({
                            'code': 'ExpiredToken',
                            'message':'Session expired, log in again'
                            })
                    }
            
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
                if path == "/admin/hello":
                    message = "Hello World!"

                elif path == "/admin/greet":
                    message = "Hi There"
                     
                elif path == "/admin/users" and "queryStringParameters" in event:
                    """ 
                    Gets list of users by type
                    Param: 'type' [REGULAR, MERCHANT]
                    Add functionality for owners to get admin list as well
                    """
                    query_params = event['queryStringParameters']
                    message = get_users_by_type(id_token, query_params=query_params)
                     
                elif path == "/admin/user" and "queryStringParameters" in event:
                    """
                    Gets a specific user by email
                    Param: 'user_email'
                    """
                    query_params = event['queryStringParameters']
                    message = get_specific_user(id_token, query_params=query_params)

                elif path == "/admin/purchase" and "queryStringParameters" in event:
                    """
                    Gets specific purchase by reference
                    Param: 'reference'
                    """
                    query_params = event['queryStringParameters']
                    message = get_purchase_by_reference(id_token, query_params=query_params)

                elif path == "/admin/tickets":
                    message = ticket_list(id_token)  
                
                elif path == "/admin/ticketsFiltered":
                    query_params = event['queryStringParameters']
                    message = get_tickets_by_status(id_token, query_params=query_params)
                
                elif "/admin/ticket":
                    query_params = event['queryStringParameters']
                    message = get_specific_ticket(id_token, query_params=query_params)
                
                else:
                # If the path is not recognized, return an error response
                    return {
                        "statusCode": 404,
                        "headers": {
                            'Access-Control-Allow-Headers': 'Content-Type',
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
                            "Content-type": 'application/json'
                        },
                        "body": json.dumps({
                            'code': 'InvalidPath',
                            'message': f'Invalid path: {path}'
                        })
                    }
                
                logging.info(message)
                status_code = 200
                response_body = {'message': message}

            if http_method == "POST":
                data = json.loads(event['body'])

                if path == "/admin/status":
                    """
                    For updating user status Active / Inactive
                    Body : {'email', 'status'}
                    """
                    message = update_user_status(id_token, data=data)

                elif path == "/admin/analytics":
                    """
                    List of all purchases by date and txnType
                    Body: {'start_date', 'end_date', 'txnType'}
                    """
                    message = transactions_by_date_range(id_token, data=data)

                elif path == "/admin/activeUsers":
                    """
                    List of active users by date range
                    Body: {'start_date', 'end_date', 'user_type'}
                    """
                    message = active_users_by_date_range(id_token, data=data)
                
                elif path == "/admin/ticketStatus":
                    """
                    Updating ticket status
                    Body: {'ticket', 'status'}
                    """

                    message = update_ticket_status(id_token, data=data)

                elif path == "/admin/addComments":
                    message = add_comments_to_ticket(id_token, data=data)
                
                

                else:
                # If the path is not recognized, return an error response
                    return {
                        "statusCode": 404,
                        "headers": {
                            'Access-Control-Allow-Headers': 'Content-Type',
                            'Access-Control-Allow-Origin': '*',
                            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
                            "Content-type": 'application/json'
                        },
                        "body": json.dumps({
                            'code': 'InvalidPath',
                            'message': f'Invalid path: {path}'
                        })
                    }
                
                logging.info(message)
                status_code = 200
                response_body = {'message': message}

        except CustomException as e:
        # Handle your custom exception and return the custom error response
            logger.error(f"Custom Exception {e}")
            status_code=400
            response_body = {"code": e.code, "message": e.message}
        
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
    
