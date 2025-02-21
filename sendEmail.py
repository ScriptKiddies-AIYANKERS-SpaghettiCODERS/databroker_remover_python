import json
import boto3
import hashlib
from datetime import datetime, timedelta

dynamodb = boto3.client('dynamodb', region_name='your_aws_region')
ses = boto3.client('ses', region_name='your_aws_region')

US_FILTER = ["Cowen"]

COMPANIES = [
    {"name": "Company1", "email": "email1@example.com"},
    {"name": "Company2", "email": "email2@example.com"},
    # Add more companies as needed
]

def lambda_handler(event, context):
    body = json.loads(event['body'])
    email = body.get('email')
    details = body.get('details')

    if not email:
        return {"success": False}

    hashed_email = hashlib.sha256(email.encode()).hexdigest()

    try:
        response = dynamodb.get_item(
            TableName='your_table_name',
            Key={'id': {'S': hashed_email}}
        )
        item = response.get('Item', {})
        can_proceed = True

        if 'lastSent' in item:
            last_sent = int(item['lastSent']['N'])
            now = datetime.utcnow()
            last_sent_date = datetime.utcfromtimestamp(last_sent)
            can_proceed = last_sent_date < now - timedelta(days=45)

        if not item.get('verified', {}).get('BOOL', False):
            can_proceed = False

        if can_proceed:
            dynamodb.update_item(
                TableName='your_table_name',
                Key={'id': {'S': hashed_email}},
                UpdateExpression='SET lastSent = :lastSent, dateDate = :dateDate',
                ExpressionAttributeValues={
                    ':lastSent': {'N': str(int(datetime.utcnow().timestamp()))},
                    ':dateDate': {'N': str(datetime.utcnow().day)}
                }
            )

            name = details.get('name')
            street = details.get('street')
            city = details.get('city')
            country = details.get('country')
            postcode = details.get('postcode')

            filtered_companies = [
                company for company in COMPANIES
                if country == "US" or company['name'] not in US_FILTER
            ]

            def create_bulk_send_command(companies, template_name):
                destinations = [
                    {
                        'Destination': {'ToAddresses': [company['email']], 'CcAddresses': [email]},
                        'ReplacementTemplateData': json.dumps({
                            'name': name,
                            'street': street,
                            'city': city,
                            'country': country,
                            'postcode': postcode,
                            'email': email,
                            'companyName': company['name']
                        })
                    }
                    for company in companies
                ]
                return {
                    'Source': 'requests@visiblelabs.org',
                    'Template': template_name,
                    'Destinations': destinations,
                    'DefaultTemplateData': json.dumps({
                        'name': 'John Doe',
                        'street': '123 Main St',
                        'city': 'Anytown',
                        'country': 'USA',
                        'postcode': '12345',
                        'email': 'example@example.com',
                        'companyName': 'Acme'
                    }),
                    'ReplyToAddresses': [email]
                }

            def split_companies_into_chunks(companies, chunk_size):
                for i in range(0, len(companies), chunk_size):
                    yield companies[i:i + chunk_size]

            chunks = list(split_companies_into_chunks(filtered_companies, 50))

            for chunk in chunks:
                bulk_send_command = create_bulk_send_command(chunk, "CompanyEmail")
                try:
                    result = ses.send_bulk_templated_email(**bulk_send_command)
                    print("result", result)
                except Exception as e:
                    print(e)

            return {"success": True}
        else:
            return {"success": False, "error": "You have already done this within the last 45 days"}
    except Exception as e:
        print(e)
        return {"success": False, "error": "Something went wrong"}
