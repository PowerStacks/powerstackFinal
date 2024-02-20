from functions import *


# ---------- SECTION 1: ANALYTICS ----------

def transactions_by_date_range(id_token, data):
    # Number of transactions by type ( Wallet funds, Regular purchases) (Simple, Wallet, Merchant) ALlow disco to only see (Merchant and Simple payment types)
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
            transaction_list['purchase_count'] = len(transaction_list['purchases'])
            transaction_list['naira_amount'] = sum(float(item["amount"]) for item in data['Items']) if data['Items'] else 0
            
            units_sold = sum_attribute_by_date_range(PURCHASE_TABLE,'txnType', type, 'purchaseDate', 'units', start_date, end_date)
            if type == 'Merchant':
                
                commission_paid_out = sum_attribute_by_date_range(PURCHASE_TABLE,'txnType', type, 'purchaseDate', 'commission', start_date, end_date)
                transaction_list['units_sold'] = units_sold
                transaction_list['commission_paid_out'] = commission_paid_out
            else:
                transaction_list['units_sold'] = sum_attribute_by_date_range(PURCHASE_TABLE,'txnType', type, 'purchaseDate', 'units', start_date, end_date)

            return transaction_list
        else:
            raise UnauthorizedUser
    except Exception as e:
       error_format(e)
    
def active_users_by_date_range(id_token, data):
    decoded_token = decode_token(id_token)
    user_type = decoded_token.get('custom:userType')

    start_date = data.get('start_date')
    end_date = data.get('end_date')
    type = data.get('user_type')
    try:
        if user_type == "OWNER":
            data = analytics(USERS_TABLE, 'userType', type, 'lastLogin', start_date, end_date)
            user_count = len(data.get('Items', []))

            return {'users': data.get('Items', []), 'user_count': user_count}
        else:
            raise UnauthorizedUser
    except Exception as e:
        error_format(e)


    