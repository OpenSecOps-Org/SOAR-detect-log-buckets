import os
import boto3

CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']

sts_client = boto3.client('sts')


def lambda_handler(data, _context):
    region = data['region']
    account_id = data['account_id']
    bucket_name = data['bucket_name']

    print(f"Checking existence of {bucket_name} in account {account_id} of region {region}...")
    s3_client = get_client('s3', account_id, region)
    s3_client.head_bucket(Bucket=bucket_name)
    print("Bucket exists.")

    print(f"Getting files...")
    s3_resource = get_resource('s3', account_id, region)
    objects = list(s3_resource.Bucket(bucket_name).objects.filter(Prefix=''))
    objects.sort(key=lambda o: o.last_modified)

    print(f"Total number of files: {len(objects)}")

    files = list(map(lambda x: x.key, objects[-10:]))
    print(files)
    return files


def get_client(client_type, account_id, region, role=CROSS_ACCOUNT_ROLE):
    other_session = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role}",
        RoleSessionName=f"get_latest_files_{account_id}"
    )
    access_key = other_session['Credentials']['AccessKeyId']
    secret_key = other_session['Credentials']['SecretAccessKey']
    session_token = other_session['Credentials']['SessionToken']
    return boto3.client(
        client_type,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
        region_name=region
    )

def get_resource(client_type, account_id, region, role=CROSS_ACCOUNT_ROLE):
    other_session = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role}",
        RoleSessionName=f"get_latest_files_{account_id}"
    )
    access_key = other_session['Credentials']['AccessKeyId']
    secret_key = other_session['Credentials']['SecretAccessKey']
    session_token = other_session['Credentials']['SessionToken']
    return boto3.resource(
        client_type,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
        region_name=region
    )
