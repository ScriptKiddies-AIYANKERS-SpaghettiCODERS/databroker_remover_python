import json
import boto3
import hashlib
import os
from botocore.exceptions import ClientError
from flask import Flask, request, jsonify

app = Flask(__name__)

dynamodb = boto3.client('dynamodb', region_name=os.environ['VITE_AWS_REGION'])

@app.route('/post', methods=['POST'])
def post():
    body = request.get_json()
    email = body.get('email')
    code = body.get('code')
    if not email or not code:
        return jsonify({'success': False})

    hashed_email = hashlib.sha256(email.encode()).hexdigest()
    params = {
        'TableName': os.environ['VITE_TABLE_NAME'],
        'Key': {
            'id': {'S': hashed_email}
        }
    }

    try:
        data = dynamodb.get_item(**params)
        if 'Item' in data:
            stored_code = data['Item']['code']['S']
            if stored_code == code:
                update_params = {
                    'TableName': os.environ['VITE_TABLE_NAME'],
                    'Key': {
                        'id': {'S': hashed_email}
                    },
                    'UpdateExpression': 'SET verified = :verified',
                    'ExpressionAttributeValues': {
                        ':verified': {'BOOL': True},
                    }
                }
                dynamodb.update_item(**update_params)
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Incorrect code'})
    except ClientError as e:
        print(e)
        return jsonify({'success': False, 'error': 'Something went wrong'})

if __name__ == '__main__':
    app.run()
