import uuid
import requests
import boto3
import logging
import json
import random

from decimal import Decimal
from botocore.exceptions import ClientError
from utils.utils import *
from utils.db_utils import * 
from utils.payment_utils import *
from utils.exception_handler import *


"""
    TODO: Things to add:
    1. Add signup and login path for admin users:
        - can be manual for now
        - one approach could be to create emails for admins, provision those emails then give them the login details
        - owner portal can have a form accessible to create an admin user
        - disco and owner users can be created manually.
    2. Restrict route access to only UI hosted domain
    2. Cors on api gateway
    4. 
"""

# ---------- LOGS ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------- GLOBALS ----------
POOL_SECRET = json.loads(get_secret('powerstack_pool', 'us-east-2'))
COGNITO_CLIENT = boto3.client('cognito-idp')
USER_POOL_ID = POOL_SECRET["powerstack_pool_id"]
USER_CLIENT_ID = POOL_SECRET["powerstack_client_id"]
USER_CLIENT_SECRET = POOL_SECRET["powerstack_client_secret"]

# ---------- DATABASE TABLES ----------
USERS_TABLE = 'powerstackUsers'
PURCHASE_TABLE = 'powerstackPurchases'
TICKETS_TABLE = 'powerstackTickets'

# ---------- FEES (SERVICE & MERCHANT COMMISSION) ----------
SERVICE = 100
COMMISSION = 0.01 # 1%

# ---------- SECTION 1: AUTHENTICATION ----------

def user_login(data):
    """
    Handles user log ins, gets idToken from cognito, and returns user info if user is still active.

    Args:
        data : username, password

    Returns:
        JSON : Id token and user info ( To be stored for access to other endpoints / populate dashboard)
    """
    try:
        username = data.get('username')
        password = data.get('password')

        # Get id token for access
        id_token = get_id_token(username, password)

        user_info = user_check(id_token)
        if user_info['user_info']['isActive'] is False:
            raise AccountDeactivatedException
        else:
            return {'idToken': id_token, 'dashboard': user_info} 
    except Exception as e:
        error_format(e)

def user_signup(data):
    """
    Handles user signups, creates the user > cognito sends verification code

    Args:
        data : username (can make this same as email ), password, email, phone_number, 
        user_type (depending on page they are signing up on), full_name

    Returns:
        JSON : Success / Error msg
    """
    try:
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        phone_number = data.get('phone_number')
        user_type = data.get('user_type')
        first_name = data.get('first_name')
        last_name = data.get('last_name')

        # Delete unconfirmed user if any
        unconfirmed_list = get_unconfirmed_users(USER_POOL_ID, COGNITO_CLIENT)
        email_unconfirmed = any(user_dict['Email'] == email for user_dict in unconfirmed_list)
        if email_unconfirmed:
            for user_dict in unconfirmed_list:
                if email == user_dict['Email']:
                    delete_user(USER_POOL_ID, user_dict['Username'], COGNITO_CLIENT)

        # Check if a user with the same email already exists
        existing_user = None
        existing_user = get_user_by_email(email, COGNITO_CLIENT, USER_POOL_ID)

        logger.info(existing_user)
        if existing_user:
            user_status = existing_user['user_status']
            if user_status == 'CONFIRMED':
                raise AccountExistsException

        # Calculate the SECRET_HASH
        secret_hash = calculate_secret_hash(username, USER_CLIENT_ID, USER_CLIENT_SECRET)

        # Create the user
        user_attributes = [
            {'Name': 'email', 'Value': email},
            {'Name': 'phone_number', 'Value': phone_number},
            {'Name': 'custom:userType', 'Value': user_type},
            {'Name': 'given_name', 'Value': first_name},
            {'Name': 'family_name', 'Value': last_name},
        ]

        response = COGNITO_CLIENT.sign_up(
            ClientId=USER_CLIENT_ID,
            Username=username,
            Password=password,
            UserAttributes=user_attributes,
            SecretHash=secret_hash
        )
        logger.info(response)

        return {"message": "User created successfully"}
    except Exception as e:
        error_format(e)


def confirm_sign_up(data):
    """
    Once verification is sent to sign up email, confirms user sign up, get's id token and creates user in DB

    Args:
        data : username, verification_code

    Returns:
        JSON : Status msg / IdToken
    """
    try:
        username = data.get('username')
        verification_code = data.get('verification_code')
        password = data.get('password')
        secret_hash = calculate_secret_hash(username, USER_CLIENT_ID,USER_CLIENT_SECRET)
        # Confirm user sign up
        COGNITO_CLIENT.confirm_sign_up(
            ClientId=USER_CLIENT_ID,
            Username=username,
            ConfirmationCode=verification_code,
            SecretHash=secret_hash
        )

        # Get an ID token
        id_token = get_id_token(username, password)


        # Create the user in DB
        user_check(id_token)

        return {
            'message': 'Sign-up confirmed and user authenticated successfully', 
            'idToken': id_token
            }
    except Exception as e:
        error_format(e)
    

def forgot_password_request(data):
    """
    Initiates the forgot password process by sending a reset code to the user's email.

    Args:
        data : username or email

    Returns:
        JSON : Success / Error msg
    """
    try:
        username_or_email = data.get('username')

        is_email = '@' in username_or_email
        if is_email:
            user_attributes = get_user_by_email(username_or_email, COGNITO_CLIENT, USER_POOL_ID)
            if user_attributes is None:
                raise UserNotFoundException
            else:
                username_or_email = user_attributes.get('username')

        secret_hash = calculate_secret_hash(username_or_email, USER_CLIENT_ID,USER_CLIENT_SECRET)
        response = COGNITO_CLIENT.forgot_password(
            ClientId=USER_CLIENT_ID,
            Username=username_or_email,
            SecretHash=secret_hash
        )

        logger.info(response)
        return {'message': 'Password reset code sent successfully'}
    except Exception as e:
        error_format(e)


def reset_password(data):
    """
    Handles the confirmation of the password reset and allows the user to set a new password.

    Args:
        data : username, verification_code, new_password

    Returns:
        JSON : Success / Error msg
    """
    try:
        username = data.get('username')
        verification_code = data.get('verification_code')
        new_password = data.get('new_password')

        is_email = '@' in username
        if is_email:
            user_attributes = get_user_by_email(username, COGNITO_CLIENT, USER_POOL_ID)
            if user_attributes is None:
                raise UserNotFoundException
            else:
                username = user_attributes.get('username')

        secret_hash = calculate_secret_hash(username, USER_CLIENT_ID,USER_CLIENT_SECRET)
        response = COGNITO_CLIENT.confirm_forgot_password(
            ClientId=USER_CLIENT_ID,
            Username=username,
            ConfirmationCode=verification_code,
            Password=new_password,
            SecretHash=secret_hash
        )

        logger.info(response)
        return {'message': 'Password reset successfully'}
    except Exception as e:
        error_format(e)


def get_id_token(username, password):
    """
    Exactly what it says

    Args:
        username (string)
        password (string)

    Returns:
        string : id_token
    """
    try:
        # Check if user unconfirmed / redirect to sign up
        unconfirmed_list = get_unconfirmed_users(USER_POOL_ID, COGNITO_CLIENT)

        # Check if the identifier is an email
        is_email = '@' in username
        if is_email:
            # Check if email unconfirmed
            email_unconfirmed = any(user_dict['Email'] == username for user_dict in unconfirmed_list)
            if email_unconfirmed:
                raise IncompleteSignupException
            
            user_attributes = get_user_by_email(username, COGNITO_CLIENT, USER_POOL_ID)
            if user_attributes is None:
                raise UserNotFoundException
            else:
                username = user_attributes.get('username')
        else:
            # Check if username unconfirmed
            username_unconfirmed = any(user_dict['Username'] == username for user_dict in unconfirmed_list)
            if username_unconfirmed:
                raise IncompleteSignupException
            
        # Calculate the SECRET_HASH
        secret_hash = calculate_secret_hash(username, USER_CLIENT_ID, USER_CLIENT_SECRET)

        auth_response = COGNITO_CLIENT.initiate_auth(
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': username,
                'PASSWORD': password,
                'SECRET_HASH': secret_hash
            },
            ClientId=USER_CLIENT_ID
        )
        id_token = auth_response['AuthenticationResult']['IdToken']
        return id_token
    except Exception as e:
        error_format(e)
    
    
# ---------- SECTION 2: GENERAL FUNCTIONS ----------

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
        return {'purchases': str(purchase_list)}
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

        meter_info = {
            'meterName': data['meterName'],
            'meterNumber': data['meterNumber'],
            'meterType': data['meterType'],
            'meterLocation': data['meterLocation']
        }

        user = get_items_by_attribute(USERS_TABLE, 'email', email)[0]
        user_id = user.get('userID')
        
        remove_item_from_list(USERS_TABLE,'userID', user_id, 'meters', meter_info)
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


def get_receipt(id_token, query_params):
    """
    Gets single purchase info from purchase table with txnRef

    Args:
        id_token (string): id_token
        query_params (dict): txnRef

    Returns:
        JSON: receipt / error msg
    """
    # TODO: take out idToken here
    decoded_token = decode_token(id_token)
    reference = query_params.get('txnRef')

    try:
        receipt = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', reference)[0]

        return {'message': 'Receipt retrieved', 'transaction_data': receipt}
    except Exception as e:
        error_format(e)


# ---------- SECTION 3: PAYMENT ----------
def initialize_pay_with_platform(id_token, data):
    """
    Function to initialize payments with diff payment platforms (paystack, flutterwave, zainpay)
    Pass in plaotform from request to select.
    Payment types: 
        - if merchant: M-FUND (merchant funding wallet)
        - if reg user: PUBLIC (no account)
                       SIMPLE (has account)
                        R-FUND (funding wallet)
    On funding wallet, will give full amount and add to wallet, however on sale:
    - will add platform percentage, service fee, in case of merchants (will leave commission in wallet as payment)
    - all burden is moved to the end user.
    
    Args:
        id_token (string): id_token
        data (JSON): email, amount, txnType, platform, meter_number, meter_type, location, payment_type

    Returns:
        _type_: _description_
    """

    try:
        email = data.get("email")
        phone_number = data.get('phone_number')
        amount = data.get("amount")
        tx_type = data.get('txn_type')
        platform = data.get('platform')
        meter_number = data.get('meter_number')
        meter_type = data.get('meter_type'),
        location = data.get('location'),

        metadata = {
            "phone_number": phone_number,
            "tx_type": tx_type,
            "platform": platform,
            "meter_number": meter_number,
            "meter_type": meter_type,
            "location": location,
        }  

        tx_ref = str(uuid.uuid4())
        metadata = json.dumps(metadata)

        response = paystack_init_payment(email, amount, tx_ref, metadata)
        return response
    except Exception as e:
        error_format(e)


def confirm_pay_with_platform(id_token, query_params):
    """
        Checks if payment went through, if so:
         - take out fees, manage commissions >  adds payment to our DB > if wallet funds update wallet
         - vend tokens > return receipts
         - add k electric specific data points to store in DB on reception of apis
    """
    tx_ref = query_params.get('txnRef')

    try:
        response = paystack_confirm_payment(tx_ref)

        message = response.get('message')
        data = response.get('data')
        if message == "Verification successful":
            metadata = json.loads(data.get('metadata'))
            logger.info(metadata)
            platform_fees = data.get('fees')
            transaction_date = data.get('transaction_date')
            amount = data.get('amount')
            
            email = metadata.get("email")
            phone_number = metadata.get("phone_number")
            platform = metadata.get("platform")
            meter_number = metadata.get("meter_number")
            #meter_type = metadata.get("meter_type")[0]
            #location = metadata.get("location")[0]
            tx_type = metadata.get("tx_type")

            purchase_data = {
                "purchaseID": tx_ref,
                "amount": Decimal(amount),
                "email": email,
                "phoneNumber": phone_number,
                "purchaseDate": transaction_date,
                "platform": platform,
                "txnType": tx_type
            }

            if tx_type == "Public" or tx_type == "Simple":
                ## Take out fees from amnt (service fee + platform fee then vend electricity)
                unit_amount = float(amount) - float(SERVICE) - float(platform_fees)
                purchase_data['units'] = Decimal(unit_amount)
                purchase_data['serviceFee'] = SERVICE
                purchase_data['platformFees'] = platform_fees
                purchase_data['meterNumber'] = meter_number
                #purchase_data['meterType'] = meter_type
                #purchase_data['location'] = location

                # TODO: remove (temporary)
                token = random.randint(10**11, (10**12)-1)
                purchase_data['token'] = token
            
            else:
                ## Funding wallets  (leave amount as is will take out fees when purchasing from wallet)
                decoded_token = decode_token(id_token)
                user = get_items_by_attribute(USERS_TABLE, 'email', email)[0]

                user_id = user.get('userID')
                wallet_balance = float(user.get('walletBalance'))
                new_wallet_balance = Decimal(wallet_balance + float(amount))
                update_table_item(USERS_TABLE, 'userID', user_id, 'walletBalance', new_wallet_balance)
                ## Get wallet amount, add amount to it
                ## Update user 
            
            ## Add payment to DB
            if check_value_in_table(PURCHASE_TABLE, "purchaseID", tx_ref) == False:
                insert_data(PURCHASE_TABLE, purchase_data)
            else:
                receipt = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', tx_ref)[0]
                return {'message': "Transaction already stored", 'receipt': receipt}

            #TODO: Vend tokens here if buying then update the purchase
        
            ## Return receipts    
            receipt = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', tx_ref)[0]  
            logger.info(receipt)                                                      
                                  
            return {'message': 'Payment successful!', 'transaction_data': receipt}
        else:
            raise CustomException(
                code='PaymentConfirmation',
                message= response.get('message')
            )
    except Exception as e:
        error_format(e)


def pay_with_wallet(id_token, data):
    # if merchant 1% discount on all transactions
    # add value showing commission eared in purchase table
    # vend token
    # may add fcn to get total commission earned
    # show reciept, add data to purchases, update wallet balance in user
    decoded_token = decode_token(id_token)
    email = decoded_token.get('email')
    phone_number = decoded_token.get('phone_number')
    try:
        user = get_items_by_attribute(USERS_TABLE, 'email', email)[0]
        user_id = decoded_token.get('userID')
        user_type = decoded_token.get('custom:userType')
        wallet_balance = float(user.get('walletBalance'))

        # METER INFO
        meter_number = data.get('meterNumber')
        meter_type = data.get('meterType')
        location = data.get('meterLocation')
        amount = float(data.get("amount"))

        purchase_id = str(uuid.uuid4())

        purchase_details = {
            'purchaseID': purchase_id,
            'date': format_date_time('Africa/Lagos'),
            'amount': Decimal(amount),
            'meterNumber': meter_number,
            'meterType': meter_type,
            'location': location,
            'email': email,
            'userType': user_type,
            'phoneNumber': phone_number
        }

        new_balance = wallet_balance
        if user_type == 'MERCHANT':
            customer_contact = data.get('customerContact')
            customer_name = data.get('customerName')

            if wallet_balance >= amount:
                #VEND ELECTRICITY HERE

                #UPDATE WALLET VALUE
                commission = COMMISSION * (amount - SERVICE)
                new_balance = Decimal(wallet_balance - amount + commission)

                #ADD INFO TO PURCHASE
                purchase_details['customerContact'] = customer_contact
                purchase_details['customerName'] = customer_name
                purchase_details['commission'] = Decimal(commission)

        else:
            if wallet_balance >= amount:
                #VEND HERE

                #UPDATE WALLET VALUE
                new_balance = Decimal(wallet_balance - amount)

        # UPDATE WALLET
        update_table_item(USERS_TABLE, 'userID', user_id, 'walletBalance', new_balance)

        # UPDATE PURCHASE TABLE
        insert_data(PURCHASE_TABLE, purchase_details)

        #return receipt
        receipt = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', purchase_id)[0]

        return {'message': f'{receipt}'}
    except Exception as e:
        error_format(e)
    
# ---------- SECTION 4: VENDING ----------