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
    - Login / Signup:
        1.Owners create an email for admins. - an owner page item
        2. Create the account.
        3. Give admins the access info, they can change their passwords.
        4. Same Sign in as regular users
        5. Owners can deactivate admins, users and disco
        6. Admins can deactivate users.

    - Transfer functions? - when no token is received and we've verified we received the payment. / withdraw from wallet?
        1. If no token received in a specific payment, trigger refund.
        2. User function: withdraw from wallet.

    - User Management: DONE (add filter to disallow admins from viewing Owner / Disco user types)
        1. View user list by type
        2. See specific user account info.
        3. Reactivate / Deactivate users
        4. Get purchases by user / reference / date?

    - Analytics:
        1. Amounts sold by time period in Naira
        2. Amounts sold by time period in Units
        3. Number of purchases by purchase type and amounts etc
        4. Traffic / Number of active customers / No of transactions

    - Ticket support: DONE
        1. Can see all submitted tickets, details and action on them, so take the ticket Update status to in progress, reply via email / phone
        Then add details to the ticket and close
        2. Can raise tickets and add details and close

"""
# ---------- LOGS ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------- DATABASE TABLES ----------
USERS_TABLE = 'powerstackUsers'
PURCHASE_TABLE = 'powerstackPurchases'
TICKETS_TABLE = 'powerstackTickets'

# ---------- SECTION 1: USER MANAGEMENT ----------

def get_users_by_type(id_token, query_params):
    decoded_token = decode_token(id_token)


    type = query_params.get('type')
    try:
        if admin_or_owner(decoded_token):
            user_list = get_items_by_attribute(USERS_TABLE, 'userType', type)
            return {'message': 'users retrieved', 'users': user_list}
        else:
            raise UnauthorizedUser
    except Exception as e:
        error_format(e)
    

def get_specific_user(id_token,  query_params):
    decoded_token = decode_token(id_token)
    user_email = query_params.get('user_email')         
    try:
        if admin_or_owner(decoded_token):
            user = get_items_by_attribute(USERS_TABLE, 'email', user_email)[0]
            purchases = get_items_by_attribute(PURCHASE_TABLE, 'email', user_email)
            return {'user info': f'{user}','purchases': purchases, 'message': 'User info retrieved.'}
        else:
            raise UnauthorizedUser
    except Exception as e:
       error_format(e)
    

def get_purchase_by_reference(id_token, query_params):
    decoded_token = decode_token(id_token)
    reference = query_params.get('reference') 
    try:
        if admin_or_owner(decoded_token):
            purchase = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', reference)
            return {'purchase': purchase}
        else:
            raise UnauthorizedUser
    except Exception as e:
        error_format(e)
    

def update_user_status(id_token, data):
    decoded_token = decode_token(id_token)
    user_email = data.get('email')
    status = data.get('status')
    try:
        if admin_or_owner(decoded_token):
            user = get_items_by_attribute(USERS_TABLE, 'email', user_email)[0]
            user_id = user.get('userID')
            update_table_item(USERS_TABLE, 'userID', user_id, 'isActive', status)
            return {'message': f'User status - {user_email} - has been updated'}
        else:
            raise UnauthorizedUser
    except Exception as e:
        error_format(e)

# ---------- SECTION 2: TICKET SUPPORT ----------
        
def update_ticket_status(id_token, query_params):
    """Update ticket status to In progress when first working on it. Then update to Done when admin is done with the ticket.
    All correspondence can be done through email / phone.

    Args:
        id_token (_type_): _description_
        data (_type_): _description_

    Returns:
        _type_: _description_
    """
    decoded_token = decode_token(id_token)


    ticket = query_params.get('ticket')
    new_status = query_params.get('status')
    try:
        if admin_or_owner(decoded_token): 
            status_update = update_table_item(TICKETS_TABLE, 'ticketID', ticket, 'ticketStatus', new_status)
            return {
                {'message': f'Ticket {ticket} status updated'}
            }
        else:
            raise UnauthorizedUser
    except Exception as e:
        error_format(e)


def add_comments_to_ticket(id_token, data):
    """After status update, then call the update status endpont to close the ticket. if ready to be closed.
    FOr subsequent comments, allow the function to append on past comments. on UI

    Args:
        id_token (_type_): _description_
        data (_type_): _description_
    """
    decoded_token = decode_token(id_token)
    comments = data.get('comments')
    ticket_id = data.get('ticket')
    try:
        if admin_or_owner(decoded_token):
            comment_update = update_table_item(TICKETS_TABLE, 'ticketID', ticket_id, 'comments', comments)
            return {'message': f'Ticket {ticket_id} updated' }
        else:
            raise UnauthorizedUser
    except Exception as e:
        error_format(e)



def get_tickets_by_status(id_token, query_params):
    decoded_token = decode_token(id_token)
    status = query_params.get('status')
    try:
        if admin_or_owner(decoded_token):
            ticket_list = get_items_by_attribute(TICKETS_TABLE, 'ticketStatus', status)
            return {'message': 'Tickets retrieved', 'tickets': ticket_list}
        else:
            raise UnauthorizedUser
    except Exception as e:
        error_format(e)


def get_specific_ticket(id_token, query_params):
    decoded_token = decode_token(id_token)
    ticket_id = query_params.get('ticket')
    try:
        if admin_or_owner(decoded_token):
            ticket_list = get_items_by_attribute(TICKETS_TABLE, 'ticketID', ticket_id)
            if (ticket_list):
                ticket = ticket_list[0]
            else:
                raise InvalidReferenceException
            return {'message': 'Ticket retrieved', 'ticket': ticket}
        else:
            raise UnauthorizedUser
    except Exception as e:
        error_format(e)

def ticket_list(id_token):
    decoded_token = decode_token(id_token)
   
    try:
        if admin_or_owner(decoded_token): 
            tickets = get_all_items(TICKETS_TABLE)
            return {
                'message': tickets
            }
        else:
            raise UnauthorizedUser
    except Exception as e:
        error_format(e)
    