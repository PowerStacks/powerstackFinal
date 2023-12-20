import uuid
import requests
import logging
from utils.db_utils import * 
from utils.utils import *
from decimal import Decimal


#Configure Logs
logger = logging.getLogger()
logger.setLevel(logging.INFO)

"""TODO: Add a function to disable access if user is inActive"""
"""
    - User Management
        1. View user list DONE
        2. See user account DONE
        3. See user purchases DONE
        4. Reactivate / Deactivate users DONE
        5. Get purchases by reference DONE

    - Ticket management
        1. Update ticket status to OPEN > DONE
        2. Can see all tickets, see details and reply to those details then update status.
        3. Total number of tickets.

    - Analytics
        1. amount sold over time in number of purchases, number of units, in naira value DONE
        2. Number of transactions DONE
        3. Active users over a specific time period DONE

"""
# DB Tables
USERS_TABLE = 'powerstackUsers'
PURCHASE_TABLE = 'powerstackPurchases'
TICKETS_TABLE = 'powerstackTickets'

 #### USER MANAGEMENT ###
def get_users_by_type(id_token, query_params):
    decoded_token = decode_token(id_token)
    user_type = decoded_token.get('custom:userType')

    type = query_params.get('type')
    try:
        if user_type == "ADMIN" or user_type == "OWNER":

            user_list = get_items_by_attribute(USERS_TABLE, 'userType', type)
            return {'message': 'users retrieved', 'users': user_list}
        else:
            return {'message': 'Unauthorized user'}
    except Exception as e:
        return {'error': str(e)}
    

def get_specific_user(id_token,  query_params):
    decoded_token = decode_token(id_token)
    user_type = decoded_token.get('custom:userType')
    logger.info("here too")
    user_email = query_params.get('user_email')         
    try:
        if user_type == "ADMIN" or user_type == "OWNER":

            user = get_items_by_attribute(USERS_TABLE, 'email', user_email)[0]
            purchases = get_items_by_attribute(PURCHASE_TABLE, 'email', user_email)
            return {'user info': f'{user}','purchases': purchases, 'message': 'User info retrieved.'}
        else:
            return {'mesage': 'Unauthorized user'}
    except Exception as e:
        return {'error': str(e)}
    

def get_purchase_by_reference(id_token, query_params):
    decoded_token = decode_token(id_token)
    user_type = decoded_token.get('custom:userType')
    
    reference = query_params.get('reference') 
    try:
        if user_type == "ADMIN" or user_type == "OWNER":
            purchase = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', reference)
            return {'purchase': purchase}
        else:
            return {'mesage': 'Unauthorized user'}
    except Exception as e:
        return {'error': str(e)}
    
def update_user_status(id_token, data):
    decoded_token = decode_token(id_token)
    user_type = decoded_token.get('custom:userType')

    user_email = data.get('email')
    status = data.get('status')
    try:
        if user_type == "ADMIN" or user_type == "OWNER":
            user = get_items_by_attribute(USERS_TABLE, 'email', user_email)[0]
            user_id = user.get('userID')
            update_table_item(USERS_TABLE, 'userID', user_id, 'isActive', status)
            return {'message': f'User status - {user_email} - has been updated'}
        else:
            return {'mesage': 'Unauthorized user'}
    except Exception as e:
        return {'error': str(e)}
    
### ANALYTICS ####

def transactions_by_date_range(id_token, data):
    # Number of transactions by type ( Wallet funds, Regular purchases)
    # List out transactions
    # Naira amt, unit amt sold, commission paid out
    decoded_token = decode_token(id_token)
    user_type = decoded_token.get('custom:userType')

    start_date = data.get('start_date')
    end_date = data.get('end_date')
    type = data.get('type')
    transaction_list = {}
    try:
        if user_type == "OWNER":
            data = analytics(PURCHASE_TABLE, 'txnType', type, 'purchaseDate', start_date, end_date)
            transaction_list['purchases'] = data.get('Items', [])
            transaction_list['purcahse_count'] = data.get(len(data['Items']))
            transaction_list['naira_amount'] = sum(float(item["amount"]) for item in data['Items']) if data['Items'] else 0
            
            if type == 'merchant':
                units_sold = sum_attribute_by_date_range(PURCHASE_TABLE,'txnType', type, 'purchaseDate', 'units', start_date, end_date)
                commission_paid_out = sum_attribute_by_date_range(PURCHASE_TABLE,'txnType', type, 'purchaseDate', 'commission', start_date, end_date)
                
                transaction_list['units_sold'] = units_sold
                transaction_list['commission_paid_out'] = commission_paid_out

            return transaction_list
        else:
            return {'mesage': 'Unauthorized user'}
    except Exception as e:
        return {'error': str(e)}
    
def active_users_by_date_range(id_token, data):
    decoded_token = decode_token(id_token)
    user_type = decoded_token.get('custom:userType')

    start_date = data.get('start_date')
    end_date = data.get('end_date')
    type = data.get('user_type')
    try:
        if user_type == "OWNER":
            data = analytics(USERS_TABLE, 'userType', type, 'lastLogin', start_date, end_date)

            return {'users': data.get('Items', [])}
        else:
            return {'mesage': 'Unauthorized user'}
    except Exception as e:
        return {'error': str(e)}
    
#### TICKET MANAGEMENT ####
def update_ticket_status(id_token, data):
    decoded_token = decode_token(id_token)
    user_type = decoded_token.get('custom:userType')

    ticket = data.get('ticket')
    new_status = data.get('status')
    try:
        if user_type == "OWNER" or user_type == "ADMIN":
            status_update = update_table_item(TICKETS_TABLE, 'ticketID', ticket, 'ticketStatus', new_status)
            return {
                'message': 'Status updated'
            }
        else:
            return {'mesage': 'Unauthorized user'}
    except Exception as e:
        return {'error': str(e)}



def ticket_list(id_token):
    decoded_token = decode_token(id_token)
    user_type = decoded_token.get('custom:userType')
    try:
        if user_type == "OWNER" or user_type == "ADMIN": 
            tickets = get_all_items(TICKETS_TABLE)
            return {
                'message': tickets
            }
        else:
            return {'mesage': 'Unauthorized user'}
    except Exception as e:
        return {'error': str(e)}