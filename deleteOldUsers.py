import boto3
from datetime import datetime, timedelta
import json

dynamodb = boto3.client('dynamodb', region_name='your_aws_region')

def lambda_handler(event, context):
    todays_date = str(datetime.utcnow().day)
    params = {
        'TableName': 'your_table_name',
        'IndexName': 'dateDate-index',
        'KeyConditionExpression': 'dateDate = :dateDate',
        'ExpressionAttributeValues': {
            ':dateDate': {'N': todays_date}
        }
    }

    try:
        data = dynamodb.query(**params)
        forty_five_days_ago = int((datetime.utcnow() - timedelta(days=45)).timestamp())
        for item in data.get('Items', []):
            if int(item['lastSent']['N']) < forty_five_days_ago:
                delete_params = {
                    'TableName': 'your_table_name',
                    'Key': {
                        'id': {'S': item['id']['S']}
                    }
                }
                dynamodb.delete_item(**delete_params)
    except Exception as err:
        return {
            'statusCode': 500,
            'body': json.dumps({'success': False, 'error': str(err)})
        }

    return {
        'statusCode': 200,
        'body': json.dumps({'success': True})
    }
