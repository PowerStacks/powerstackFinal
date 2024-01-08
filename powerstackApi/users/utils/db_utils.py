import json
import boto3
import uuid
import requests
import decimal

from datetime import datetime, timedelta
from utils.exception_handler import *
from boto3.dynamodb.conditions import Key, Attr

# ---------- DYNAMO DB CLIENT ----------
dynamodb =  boto3.client('dynamodb')

def get_all_items(table_name):
    dynamodb_resource = boto3.resource('dynamodb')
    table = dynamodb_resource.Table(table_name)

    response = table.scan()
    items = response.get('Items', [])

    # If the table has more items, continue scanning
    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        items.extend(response.get('Items', []))

    return items


def insert_data(table_name, data):
    dynamodb_resource = boto3.resource('dynamodb')
    table = dynamodb_resource.Table(table_name)

    response = table.put_item(Item=data)

    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return "Data inserted successfully."
    else:
        return "Failed to insert data."
    

def get_item(table_name, item_id):
    dynamodb_resource = boto3.resource('dynamodb')
    table = dynamodb_resource.Table(table_name)

    response = table.get_item(Key=item_id)
    if 'Item' in response:
        item = response['Item']
        return item
    else:
        return None
    

def get_items_by_attribute(table_name, attribute_name, attribute_value):
    dynamodb_resource = boto3.resource('dynamodb')
    table = dynamodb_resource.Table(table_name)
    response = table.scan(
        FilterExpression=Attr(attribute_name).eq(attribute_value)
    )

    items = response.get('Items', [])

    # Convert decimal values to strings
    items = [convert_decimal_to_string(item) for item in items]
    return items


def get_user_id_by_phone(phone):
    dynamodb_resource = boto3.resource('dynamodb')
    table = dynamodb_resource.Table('PowerstackUsers')

    response = table.scan(
        FilterExpression=Attr('phoneNumber').eq(phone)
    )

    items = response.get('Items', [])
    if items:
        return items[0]['userID']
    else:
        return None
    
def check_value_in_table(table_name, attribute_name, attribute_value):
    try:
        # Create a scan operation with the filter expression
        response = dynamodb.scan(
            TableName=table_name,
            FilterExpression=f"{attribute_name} = :value",
            ExpressionAttributeValues={
                ":value": {"S": attribute_value}  # Adjust the data type as per your attribute
            }
        )

        # Check if any items match the filter expression
        items = response.get('Items',[])
        return len(items) > 0
    except Exception as e:
        error_format(e)

def check_item_exists(table_name, attribute_name, attribute_value):
    dynamodb_resource = boto3.resource('dynamodb')
    table = dynamodb_resource.Table(table_name)

    try:
        response = table.scan(
            FilterExpression=Attr(attribute_name).eq(attribute_value)
        )
        items = response.get('Items', [])
        if len(items) > 0:
            return True
        else:
            return False
    except Exception as e:
        error_format(e)


def update_table_item(table_name, primary_key_name, primary_key_value, attribute_name, new_value):
    try:
        dynamodb_resource = boto3.resource('dynamodb')
        table = dynamodb_resource.Table(table_name)

        key = {
            primary_key_name: primary_key_value
        }
        update_expression = f'SET {attribute_name} = :new_value'
        expression_attribute_values = {':new_value': new_value}
        table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        return "Wallet balance updated"
    except Exception as e:
        error_format(e)


def add_item_to_list(table_name, primary_key_name, primary_key_value, attribute_name, items_to_add):
    try:
        dynamodb_resoure = boto3.resource('dynamodb')
        table = dynamodb_resoure.Table(table_name)

        # Update values in the item
        key = {primary_key_name: primary_key_value}
        update_expression = f'SET {attribute_name} = list_append({attribute_name}, :items)'
        expression_attribute_values = {':items': [items_to_add]}
        table.update_item(
            Key=key,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        return "Item Added to list"
    except Exception as e:
        error_format(e)


def remove_item_from_list(table_name, primary_key_name, primary_key_value, attribute_name, item_to_remove):
    try:
        dynamodb_resource = boto3.resource('dynamodb')
        table = dynamodb_resource.Table(table_name)

        # Get the existing list
        response = table.get_item(Key={primary_key_name: primary_key_value})
        existing_list = response['Item'].get(attribute_name, [])

        # Remove the item if it exists in the list
        if item_to_remove in existing_list:
            existing_list.remove(item_to_remove)

        # Update the item with the modified list
        table.update_item(
            Key={primary_key_name: primary_key_value},
            UpdateExpression=f'SET {attribute_name} = :newList',
            ExpressionAttributeValues={':newList': existing_list}
        )

        return "Item Removed from list"
    except Exception as e:
        error_format(e)
    
    
def get_item_count(table_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # Use the scan operation to get the count of items in the table
    response = table.scan(Select='COUNT')

    # The count is available in the 'Count' attribute of the response
    item_count = response['Count']

    return item_count


def count_records_by_date_range(table_name, date_attribute, start_date, end_date):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    start_datetime = datetime.strptime(start_date, '%Y-%m-%d %H:%M')
    end_datetime = datetime.strptime(end_date, '%Y-%m-%d %H:%M')

    filter_expression = f"{date_attribute} BETWEEN :start_date AND :end_date"

    expression_attribute_values = {
        ":start_date": start_datetime.strftime('%Y-%m-%d %H:%M'),
        ":end_date": end_datetime.strftime('%Y-%m-%d %H:%M')
    }

    response = table.scan(FilterExpression=filter_expression, ExpressionAttributeValues=expression_attribute_values)

    return len(response['Items'])


def sum_attribute_by_date_range(table_name, date_attribute, attribute_to_sum, start_date, end_date):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    start_datetime = datetime.strptime(start_date, '%Y-%m-%d %H:%M')
    end_datetime = datetime.strptime(end_date, '%Y-%m-%d %H:%M')

    filter_expression = f"{date_attribute} BETWEEN :start_date AND :end_date"

    expression_attribute_values = {
        ":start_date": start_datetime.strftime('%Y-%m-%d %H:%M'),
        ":end_date": end_datetime.strftime('%Y-%m-%d %H:%M')
    }

    response = table.scan(FilterExpression=filter_expression, ExpressionAttributeValues=expression_attribute_values)

    sum_result = sum(float(item[attribute_to_sum]) for item in response['Items']) if response['Items'] else 0

    return sum_result


def get_items_by_attribute_and_date_range(table_name, attribute_name, attribute_value, date_attribute, start_date, end_date):
    dynamodb_resource = boto3.resource('dynamodb')
    table = dynamodb_resource.Table(table_name)

    # Convert string dates to datetime objects
    start_datetime = datetime.strptime(start_date, '%Y-%m-%d %H:%M')
    end_datetime = datetime.strptime(end_date, '%Y-%m-%d %H:%M')

    filter_expression = f"{date_attribute} BETWEEN :start_date AND :end_date and {attribute_name} = :attribute_value"

    expression_attribute_values = {
        ":start_date": start_datetime.strftime('%Y-%m-%d %H:%M'),
        ":end_date": end_datetime.strftime('%Y-%m-%d %H:%M'),
        ":attribute_value": attribute_value
    }
    
    response = table.scan(FilterExpression=filter_expression, ExpressionAttributeValues=expression_attribute_values)

    items = response.get('Items', [])
    return items

def convert_decimal_to_string(obj):
    if isinstance(obj, decimal.Decimal):
        return str(obj)
    return obj