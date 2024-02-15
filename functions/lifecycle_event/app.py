import os
import json
import boto3
import uuid


LOG_ARCHIVE_ACCOUNT_ID = os.environ['LOG_ARCHIVE_ACCOUNT_ID']
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']

CLIENT = boto3.client('stepfunctions')


def lambda_handler(event, _context):
    detail = event['detail']
    process(detail)
    return True


def process(detail):
    event_name = detail['eventName']
    region = detail['awsRegion']
    account_id = detail['recipientAccountId']
    bucket_name = detail['requestParameters']['bucketName']

    print(f"Lifecycle Event: {event_name} in {region}, account {account_id}, bucket '{bucket_name}'")

    if account_id == LOG_ARCHIVE_ACCOUNT_ID:
        print('Log Archive buckets are excepted. Terminating.')
        return

    if event_name == 'CreateBucket':
        create_bucket(region, account_id, bucket_name)
    elif event_name == 'DeleteBucket':
        delete_bucket(region, account_id, bucket_name)
    else:
        print("Unsupported event. Terminating.")


def create_bucket(region, account_id, bucket_name):
    print("Bucket creation detected.")

    if is_duplicate_execution(bucket_name):
        print(f"An active execution for bucket {bucket_name} already exists. Skipping.")
        return

    print("No content monitoring job running. Starting Step Function...")
    execution_name = f"{uuid.uuid4()}-{region}-{account_id}-{bucket_name}"[:80]
    CLIENT.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=execution_name,
        input=json.dumps({
            "region": region,
            "account_id": account_id,
            "bucket_name": bucket_name
        })
    )


def is_duplicate_execution(bucket_name):
    paginator = CLIENT.get_paginator('list_executions')
    page_iterator = paginator.paginate(
        stateMachineArn=STATE_MACHINE_ARN,
        statusFilter='RUNNING'
    )
    
    for page in page_iterator:
        for execution in page['executions']:
            try:
                execution_input = json.loads(execution['input'])
                if execution_input.get('bucket_name') == bucket_name:
                    return True
            except json.JSONDecodeError:
                continue
    return False

    
def delete_bucket(region, account_id, bucket_name):
    print("Bucket deletion detected. Duly noted.")
