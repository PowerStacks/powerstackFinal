
import logging
import re

# ---------- LOGS ----------
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# ---------- SECTION 1: CUSTOM EXCEPTIONS ----------
class CustomException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message
        super().__init__(message)

class UserNotFoundException(CustomException):
    def __init__(self, message='User not found, check email / username'):
        super().__init__(code='UserNotFound', message=message)

class AccountDeactivatedException(CustomException):
    def __init__(self, message='Your account has been deactivated contact customer service for assistance.'):
        super().__init__(code='AccountDeactivated', message=message)

class AccountExistsException(CustomException):
    def __init__(self, message='User with the same email exists, go to login page'):
        super().__init__(code='AccountExists', message=message)

class IncompleteSignupException(CustomException):
    def __init__(self, message='User sign up incomplete, return to sign up page.'):
        super().__init__(code='IncompleteSignup', message=message)

class InvalidReferenceException(CustomException):
    def __init__(self, message='The given transaction reference is invalid.'):
        super().__init__(code='InvalidReference')

class InsufficientBalanceException(CustomException):
    def __init__(self, message='Insufficient wallet balance, please fund wallet.'):
        super().__init__(code='InsufficientBalance')

# ---------- SECTION 2: EXCEPTION FORMATTING ----------
def error_format(e):
    logger.info(e)
    error = str(e)
    logger.info(error)

    if isinstance(e, CustomException):
        raise e
    
    code_match = re.search(r'\((.*?)\)', error)
    msg_match = match = re.search(r':\s*(.*)', error)
    if code_match and msg_match:
        error_code = code_match.group(1)
        error_msg = msg_match.group(1)
        raise CustomException(
            code=error_code,
            message=error_msg
            )
    else:
        raise CustomException(
            code='UnhandledException',
            message=error
        )      