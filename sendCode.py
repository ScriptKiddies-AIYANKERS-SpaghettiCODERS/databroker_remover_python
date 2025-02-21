import json
import boto3
import hashlib
import os
import secrets
from botocore.exceptions import ClientError
from flask import Flask, request, jsonify

app = Flask(__name__)

dynamodb = boto3.client('dynamodb', region_name=os.environ['VITE_AWS_REGION'])
ses = boto3.client('ses', region_name=os.environ['VITE_AWS_REGION'])

@app.route('/post', methods=['POST'])
def post():
    body = request.get_json()
    otp_code = secrets.token_hex(6)
    email = body.get('email')
    if not email:
        return jsonify({'success': False})

    hashed_email = hashlib.sha256(email.encode()).hexdigest()
    check_if_email_exists_params = {
        'TableName': os.environ['VITE_TABLE_NAME'],
        'Key': {
            'id': {'S': hashed_email}
        }
    }

    try:
        data = dynamodb.get_item(**check_if_email_exists_params)
        if 'Item' in data and 'lastSent' in data['Item']:
            return jsonify({
                'success': False,
                'error': "You've already done this within the last 45 days"
            })
    except ClientError as e:
        print(e)
        return jsonify({'success': False, 'error': 'Something went wrong'})

    params = {
        'TableName': os.environ['VITE_TABLE_NAME'],
        'Item': {
            'id': {'S': hashed_email},
            'code': {'S': otp_code}
        }
    }

    template_data = {
        'code': otp_code
    }

    ses_send_template_input = {
        'Destination': {
            'ToAddresses': [email]
        },
        'Source': 'noreply@visiblelabs.org',
        'Template': 'VerificationCode',
        'TemplateData': json.dumps(template_data)
    }

    try:
        dynamodb.put_item(**params)
        ses.send_templated_email(**ses_send_template_input)
        return jsonify({'success': True})
    except ClientError as e:
        print(e)
        return jsonify({'success': False, 'error': 'Something went wrong'})

if __name__ == '__main__':
    app.run()
