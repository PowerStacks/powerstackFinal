import random

from functions import *

# ---------- FEES (MERCHANT COMMISSION) ----------
COMMISSION = 0.01 # 1%

def initialize_pay_with_platform(data):
    """
    Function to initialize payments with diff payment platforms (paystack, flutterwave, zainpay)
    Pass in plaotform from request to select.
    Payment types: 
        - Wallet
        - Simple
        - Merchant is only allowed to use this to fund wallet
        - Reguler users can do a straight up purchase, guest checkout and wallet fund
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
        meter_number = data.get('meter_number') # Not needed for wallet pay
        meter_type = data.get('meter_type') # Not needed for wallet pay
        location = data.get('location') # Not needed for wallet pay

        metadata = {
            "phone_number": phone_number,
            "tx_type": tx_type,
            "platform": platform,
            "meter_number": meter_number,
            "meter_type": meter_type,
            "location": location,
        }

        tx_ref = str(uuid.uuid4())

        #TODO: replace callback url with our domain url
        #TODO: add the payment id and prelim info to db then update entry in the confirm pay
        # ---------- ADD PAYMENT TO DB ----------
        purchase_data = metadata
        purchase_data["purchaseID"] = tx_ref
        purchase_data["amount"] = str(float(amount) / 100) # amount to naira
        purchase_data["status"] = "Initialized"
        insert_data(PURCHASE_TABLE, purchase_data)

        callback_url = "http://127.0.0.1:5000/receipt/" + tx_ref + "?confirm=true"
        metadata = json.dumps(metadata)

        response = paystack_init_payment(email, amount, tx_ref, metadata, callback_url)
        return response
    except Exception as e:
        error_format(e)


def confirm_pay_with_platform(query_params):
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
        transaction_status = data.get('status')

        if message == "Verification successful" and transaction_status == "success":

            metadata = json.loads(data.get('metadata'))

            platform_fees = float(data.get('fees')) / 100 # to Naira from Kobo
            amount = float(data.get('amount')) / 100 # to Naira from Kobo
            transaction_date = data.get('transaction_date')
            email = data.get("customer").get("email")
            phone_number = metadata.get("phone_number")

            platform = metadata.get("platform")
            meter_number = metadata.get("meter_number")
            meter_type = metadata.get("meter_type")
            location = metadata.get("location")
            tx_type = metadata.get("tx_type")
            logger.info("HERE")
            purchase_data = {
                "purchaseID": tx_ref,
                "amount": str(amount),
                "email": email,
                "phoneNumber": phone_number,
                "purchaseDate": transaction_date,
                "paymentMethod": platform,
                "txnType": tx_type,
                "platformFees": str(platform_fees)
            }

            # ---------- SIMPLE PAYMENT ----------
            if tx_type == "Simple":
                # Take out fees from amnt (service fee + platform fee then vend electricity)

                unit_amount = float(amount) - service_fee(amount) - float(platform_fees) # amount paid - service fee - platform fees
                purchase_data['units'] = str(unit_amount)
                purchase_data['serviceFee'] = str(service_fee(amount))
                purchase_data['meterNumber'] = meter_number
                purchase_data['meterType'] = meter_type
                purchase_data['location'] = location

                # TODO: remove (temporary) - replace with token vending here
                token = random.randint(10**11, (10**12)-1)
                purchase_data['token'] = token
                logger.info("HEREE")

            # ---------- FUND WALLET ----------
            if tx_type == "Wallet":
                # Funding wallets  (leave amount as is will take out fees when purchasing from wallet)

                user = get_items_by_attribute(USERS_TABLE, 'email', email)[0]

                user_id = user.get('userID')
                wallet_balance = float(user.get('walletBalance'))

                new_wallet_balance = str(wallet_balance + float(amount))
                update_table_item(USERS_TABLE, 'userID', user_id, 'walletBalance', new_wallet_balance)

                purchase_data['wallet_balance'] = new_wallet_balance
                logger.info("HERRE")
            
            # ---------- ADD PAYMENT TO DB ----------
            stored_purchase = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', tx_ref)[0]
            if stored_purchase.get("status") == "Initialized":
                purchase_data["status"] = "Confirmed"
                insert_data(PURCHASE_TABLE, purchase_data)

            else:
                return {'message': "Transaction already stored", 'receipt': stored_purchase}
        
            # ---------- RETURN RECEIPT ----------   
            receipt = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', tx_ref)[0]                                                                     
            return {'message': 'Payment successful!', 'transaction_data': receipt}
        else:
            raise CustomException(
                code='PaymentStatus',
                message = "Transaction status: " + transaction_status
            )
    except Exception as e:
        error_format(e)


def pay_with_wallet(id_token, data):
    # if merchant 1% discount on all transactions ( will not take out the full amount - will take out amount - 1%)
    # vend token
    # may add fcn to get total commission earned
    # show reciept, add data to purchases, update wallet balance in user
    decoded_token = decode_token(id_token)
    email = decoded_token.get('email')
    phone_number = decoded_token.get('phone_number')
    try:
        user = get_items_by_attribute(USERS_TABLE, 'email', email)[0]
        user_id = user.get('userID')
        user_type = decoded_token.get('custom:userType')
        wallet_balance = float(user.get('walletBalance'))
        logger.info("IM here")
        # METER INFO
        meter_number = data.get('meter_number')
        meter_type = data.get('meter_type')
        location = data.get('meter_location')
        amount = float(data.get("amount")) / 100

        purchase_id = str(uuid.uuid4())

        purchase_details = {
            'purchaseID': purchase_id,
            'amount': str(amount),
            'email': email,
            'phoneNumber': phone_number,
            'purchaseDate': format_date_time('Africa/Lagos'),
            'txnType': "Wallet",
            'meterNumber': meter_number,
            'meterType': meter_type,
            'location': location,   
        }


        unit_amount = amount - service_fee(amount) - platform_fee(amount)
        new_balance = wallet_balance
        logger.info("Here")
        if wallet_balance >= amount:
            if user_type == 'MERCHANT':
                customer_contact = data.get('customerContact')
                customer_name = data.get('customerName')

                
                    #VEND ELECTRICITY HERE
                
                    #UPDATE WALLET VALUE
                    
                commission = COMMISSION * amount
                new_balance = str(wallet_balance - amount + commission)
                logger.info("Here 3")
                #ADD INFO TO PURCHASE
                purchase_details['units'] = str(unit_amount)
                purchase_details['serviceFee'] = str(service_fee(amount))
                purchase_details['platformFees'] = str(platform_fee(amount))
                purchase_details['customerContact'] = customer_contact
                purchase_details['customerName'] = customer_name
                purchase_details['commission'] = str(commission)
                purchase_details['payment_method'] = "MERCHANT"
                logger.info("here 4")
                # TODO: remove (temporary) - replace with token vending below
                token = random.randint(10**11, (10**12)-1)
                purchase_details['token'] = token
                logger.info("HEREE")

            else:
            
                #VEND HERE

                #UPDATE WALLET VALUE
                new_balance = str(wallet_balance - amount)

                purchase_details['units'] = str(unit_amount)
                purchase_details['serviceFee'] = str(service_fee(amount))
                purchase_details['platformFees'] = str(platform_fee(amount))
                # TODO: remove (temporary) - replace with token vending below
                token = random.randint(10**11, (10**12)-1)
                purchase_details['token'] = token
                logger.info("HEREE")
        else:
            raise CustomException(
                code='InsufficientBalance',
                message = "Insufficient wallet balance, please fund wallet." 
            )
        # ---------- UPDATE WALLET ----------
        update_table_item(USERS_TABLE, 'userID', user_id, 'walletBalance', new_balance)

        # ---------- ADD PAYMENT TO DB ----------
        if check_value_in_table(PURCHASE_TABLE, "purchaseID", purchase_id) == False:
                purchase_details["status"] = "Confirmed"
                insert_data(PURCHASE_TABLE, purchase_details)
        else:
            receipt = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', purchase_id)[0]
            return {'message': "Transaction already stored", 'receipt': receipt}

        # ---------- RETURN RECEIPT ----------
        receipt = get_items_by_attribute(PURCHASE_TABLE, 'purchaseID', purchase_id)[0]                                                                         
        return {'message': 'Payment successful!', 'transaction_data': receipt}

    except Exception as e:
        error_format(e)