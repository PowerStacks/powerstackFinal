from functions import *

# ---------- GLOBALS ----------
POOL_SECRET = json.loads(get_secret('powerstack_pool', 'us-east-2'))
COGNITO_CLIENT = boto3.client('cognito-idp')
USER_POOL_ID = POOL_SECRET["powerstack_pool_id"]
USER_CLIENT_ID = POOL_SECRET["powerstack_client_id"]
USER_CLIENT_SECRET = POOL_SECRET["powerstack_client_secret"]


# ---------- AUTH FUNCTIONS ----------
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