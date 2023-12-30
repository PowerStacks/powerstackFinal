import boto3
import json
import pytz
import jwt
import logging
import re
import hashlib, hmac, base64

from datetime import datetime, timezone
from botocore.exceptions import ClientError

# ---------- LOGS ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def format_date_time(timezone_id):
    time_zone = pytz.timezone(timezone_id)
    local_time = time_zone.localize(datetime.now())
    return local_time.strftime('%Y-%m-%d %H:%M')


def decode_token(id_token):
    decoded_token = jwt.decode(id_token, algorithms="RS256", options={"verify_signature": False})
   
    current_time = datetime.now(timezone.utc).timestamp()
    expiration_time = decoded_token['exp']
    if current_time < expiration_time:
        return decoded_token
    else:
        return "Expired"


def get_secret(secret_name, region_name):
    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    # Decrypts secret using the associated KMS key.
    secret = get_secret_value_response['SecretString']
    return secret

def calculate_secret_hash(username, client_id, client_secret):
    message = username + client_id
    dig = hmac.new(str(client_secret).encode('utf-8'), 
                   msg=str(message).encode('utf-8'), 
                   digestmod=hashlib.sha256).digest()
    
    secret_hash = base64.b64encode(dig).decode()
    return secret_hash

def get_user_by_email(email, client, pool_id):
    try:
        response = client.admin_get_user(
            UserPoolId=pool_id,
            Username=email
        )
        logger.info(response)
        # The user details are available in the 'UserAttributes' field of the response
        user_attributes = response.get('UserAttributes')
        username = response.get('Username')
        user_status = response.get('UserStatus')
        return {
            'username': username, 
            'user_status': user_status, 
            'user_attributes': user_attributes
            }
    except client.exceptions.UserNotFoundException:
        return None
    except Exception as e:
        raise Exception(str(e))
    

def get_unconfirmed_users(user_pool_id, client):
    try:
        response = client.list_users(
            UserPoolId=user_pool_id,
            AttributesToGet=['email'],
            Filter="cognito:user_status = \"UNCONFIRMED\""
        )
        logger.info(response)
        unconfirmed_users = [{'Username': user['Username'], 'Email': user['Attributes'][0]['Value']} for user in response['Users']]
        logger.info(unconfirmed_users)
        return unconfirmed_users
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None
    

def delete_user(user_pool_id, username, client):
    try:
        client.admin_delete_user(
            UserPoolId=user_pool_id,
            Username=username
        )
        print(f"User {username} deleted successfully.")
    except Exception as e:
        print(f"An error occurred while deleting the user: {str(e)}")