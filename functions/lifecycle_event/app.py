import os
import json
import boto3

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
    print("Bucket creation detected. Starting Step Function...")
    CLIENT.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=f'{region}-{account_id}-{bucket_name}'[0:80],
        input=json.dumps({
            "region": region,
            "account_id": account_id,
            "bucket_name": bucket_name
        })
    )

    
def delete_bucket(region, account_id, bucket_name):
    print("Bucket deletion detected. Duly noted.")
