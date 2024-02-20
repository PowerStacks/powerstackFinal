import uuid
import boto3
import logging
import json

from utils.general_utils import *
from utils.db_utils import * 
from utils.payment_utils import *
from utils.exception_handler import *


"""
    TODO: Things to add:
    1. Add signup and login path for admin users:
        - can be manual for now
        - one approach could be to create emails and usernames for admins, provision those emails then give them the login details
        - owner portal can have a form accessible to create an admin user
        - disco and owner users can be created manually.
    2. Restrict route access to only UI hosted domain
    3. Cors on api gateway
    4. finish admin fcns
    5. test deployment 
    6. docs
    7. future dev > referral codes, whatsapp integration etc
    8. Handle all cases for all functions eg ticket issue, 
    FRI:
    - plan for admin
    - standardize purchaseID - DONE
    - docs layout
    SAT:
    - finish admin docs
    - api documentation
    - look into date issue w timezone.
    SUN:
    - begin testing deployment
    - start admin work
"""

# ---------- LOGS ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------- DATABASE TABLES ----------
USERS_TABLE = 'powerstackUsers'
PURCHASE_TABLE = 'powerstackPurchases'
TICKETS_TABLE = 'powerstackTickets'

# ---------- GENERAL FUNCTIONS ----------

def user_check(id_token):
    """
    Dashboard function - gets user info from DB if user exists.
    If user doesn't exist, creates user profile in DB

    Args:
        id_token (string)

    Returns:
        JSON : success message
    """
    decoded_token = decode_token(id_token)

    try:
        email = decoded_token['email']
        phone_number = decoded_token.get('phone_number', None)
        user_type = decoded_token.get('custom:userType', None)
        first_name = decoded_token.get('given_name', None)
        last_name = decoded_token.get('family_name', None)
        
        if check_item_exists(USERS_TABLE, 'email', email):
            user = get_items_by_attribute(USERS_TABLE, 'email', email)[0]
            user['walletBalance'] = float(user.get('walletBalance'))

            user_id = user.get('userID')

            update_table_item(USERS_TABLE, 'userID', user_id, 'lastLogin', format_date_time('Africa/Lagos'))
            
            return {'user_info': user, 'message': 'User info retrieved.'}
        else:    
            user_attributes = {
                'userID': str(uuid.uuid4()),
                'phoneNumber': phone_number,
                'email': email,
                'userType': user_type,
                'firstName': first_name,
                'lastName': last_name,
                'isActive': True,
                'lastLogin': format_date_time('Africa/Lagos'),
                'walletBalance': 0,
                'meters': []
            }
            
            insert_data(USERS_TABLE, user_attributes)
            return {'message': 'User added to database.'}
    except Exception as e:
        error_format(e)


def purchase_history(id_token):
    """
        Returns list of purchases based on user email.
        Used for both REGULAR and MERCHANT accts
        :param decoded_token:  User info from JWT token
        :return: list of past purchases
    """
    """
    Returns list of purchases based on user email.
    Used for both REGULAR and MERCHANT accts

    Args:
        string: id_token

    Returns:
        JSON: list of all user purchases
    """
    decoded_token = decode_token(id_token)
    try:
        email_attr = 'email'
        email = decoded_token[email_attr] #use email as main query method
        purchase_list = get_items_by_attribute(PURCHASE_TABLE, email_attr, email)
        return {'message': purchase_list}
    except Exception as e:
        error_format(e)
    

def add_meter(id_token, data):
    """
    Adds meter to user account.

    Args:
        id_token (string): id token 
        data (dict): meterName, meterNumber, meterType, meterLocation

    Returns:
        JSON : success / error info
    """
    decoded_token = decode_token(id_token)

    try:
        email = decoded_token['email']
        # TODO: Validate meter with disco API, check if meter is in list, if not then add to the meters list

        meter_info = {
            'meterName': data.get('meterName', None),
            'meterNumber': data.get('meterNumber', None),
            'meterType': data.get('meterType', None),
            'meterLocation': data.get('meterLocation', None)
        }

        user = get_items_by_attribute(USERS_TABLE, 'email', email)[0]
        user_id = user.get('userID')
        meters = user.get('meters')

        for stored_meter in meters:
            # Check if meter already exists
            if all(meter_info[key] == stored_meter[key] for key in meter_info):
                return {'message': 'Meter already saved.'}
            
        # Add the new meter to list
        add_item_to_list(USERS_TABLE, 'userID', user_id, 'meters', meter_info)
        return {'message': 'Meter info saved.'}

    except Exception as e:
        error_format(e)


def remove_meter(id_token, data):
    """
    Removes meter from meters list

    Args:
        id_token (string): id token 
        data (dict): meterName, meterNumber, meterType, meterLocation

    Returns:
        JSON: success / error msg
    """
    decoded_token = decode_token(id_token)

    try:
        email = decoded_token['email']

        meter_number = data['meterNumber']
        

        user = get_items_by_attribute(USERS_TABLE, 'email', email)[0]
        user_id = user.get('userID')
        
        remove_item_from_list(USERS_TABLE,'userID', user_id, 'meters', meter_number)
        return {'message': 'Meter removed!'}
    
    except Exception as e:
        error_format(e)
    

def submit_ticket(id_token, data):
    """
    Allows user to create and submit tickets.

    Args:
        id_token (string): id_token
        data (dict): details 

    Returns:
        JSON : tix id / error info
    """
    #TODO: Implement email notifications for customer service email with tix info , add func. for claiming / updating tix status.
    # Submit ticket to table > Trigger Email notif > Customer service rep can reply > update the ticket status

    decoded_token = decode_token(id_token)

    try:
        item_count = get_item_count(TICKETS_TABLE) + 1
        email = decoded_token['email']
        user_type = decoded_token['custom:userType']
        ticket_id = 'PST-' + str(item_count)
        ticket_data = {
            'ticketID': ticket_id,
            'email': email,
            'userType': user_type,
            'details': data.get('details', None),
            'ticketStatus': 'NEW'  
        }
        insert_data(TICKETS_TABLE, ticket_data)
        # trigger email here
        return {'message': f'Ticket ID: {ticket_id}'}
    except Exception as e:
        error_format(e)


def get_receipt(query_params):
    """
    Gets single purchase info from purchase table with txnRef

    Args:
        id_token (string): id_token
        query_params (dict): txnRef

    Returns:
        JSON: receipt / error msg
    """
    # TODO: take out idToken here
    #decoded_token = decode_token(id_token)
    reference = query_params.get('txnRef')

    try:
        receipt_list = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', reference)
        if (receipt_list):
            receipt = receipt_list[0]
        else:
            raise InvalidReferenceException
        return {'message': 'Receipt retrieved', 'transaction_data': receipt}
    except Exception as e:
        error_format(e)