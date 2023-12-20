import boto3
import json
import pytz
import jwt

from datetime import datetime
from botocore.exceptions import ClientError


def user_pool_creds(secret_name, region):
    """
    Gets value of secrets stored in secrets manager
    """
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
    secret = json.loads(get_secret_value_response['SecretString'])
    return secret


def format_date_time(timezone_id):
    time_zone = pytz.timezone(timezone_id)
    local_time = time_zone.localize(datetime.now())
    return local_time.strftime('%Y-%m-%d %H:%M')


def decode_token(id_token):
    # id_token = event['headers']['Authorization'].split()[1]
    decoded_token = jwt.decode(id_token, algorithms="RS256", options={"verify_signature": False})
    return decoded_token