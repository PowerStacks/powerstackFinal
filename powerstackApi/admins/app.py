import json
import logging

from functions import * 
# import requests

#Configure Logs
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        return json.JSONEncoder.default(self, obj)
    

def lambda_handler(event, context):
    logger.info(f"event {event}")
    response_body = {"error": "Invalid request"}
    status_code = 400

    id_token = None
    message = None
    if "httpMethod" in event:

        if 'headers' in event and 'Authorization' in event['headers']:
            authorization_header = event['headers']['Authorization']
            if authorization_header.startswith('Bearer '):
                id_token = authorization_header.split()[1]
            else:
                logger.info("Invalid Id token")

        try:
            http_method = event["httpMethod"]
            path = event["path"]


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

            if http_method == "GET":
                if path == "/admin/hello":
                    message = "Hello World!"

                if path == "/admin/greet":
                    message = "Hi There"
                     
                if path == "/admin/users" and "queryStringParameters" in event:
                    """ 
                    Gets list of users by type
                    Param: 'type' [REGULAR, MERCHANT]
                    Add functionality for owners to get admin list as well
                    """
                    query_params = event['queryStringParameters']
                    message = get_users_by_type(id_token, query_params=query_params)
                     
                if path == "/admin/user" and "queryStringParameters" in event:
                    """
                    Gets a specific user by email
                    Param: 'user_email'
                    """
                    query_params = event['queryStringParameters']
                    logger.info("I got here")
                    message = get_specific_user(id_token, query_params=query_params)

                if path == "/admin/purchase" and "queryStringParameters" in event:
                    """
                    Gets specific purchase by reference
                    Param: 'reference'
                    """
                    query_params = event['queryStringParameters']
                    message = get_purchase_by_reference(id_token, query_params=query_params)

                if path == "/admin/tickets":
                    message = ticket_list(id_token)  
                
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

                if path == "/admin/analytics":
                    """
                    List of all purchases by date and txnType
                    Body: {'start_date', 'end_date', 'txnType'}
                    """
                    message = transactions_by_date_range(id_token, data=data)

                if path == "/admin/activeUsers":
                    """
                    List of active users by date range
                    Body: {'start_date', 'end_date', 'user_type'}
                    """
                    message = active_users_by_date_range(id_token, data=data)
                
                if path == "/admin/ticketStatus":
                    """
                    Updating ticket status
                    Body: {'ticket', 'status'}
                    """

                    message = update_ticket_status(id_token, data=data)
                
                logging.info(message)
                status_code = 200
                response_body = {'message': message}

        except Exception as e:
            logger.info(f"Error {e}")
            status_code = 500
            response_body = {"error": "Internal server error"}
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
    
