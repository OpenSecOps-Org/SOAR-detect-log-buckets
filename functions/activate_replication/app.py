import os
import boto3

CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']
REPLICATION_ROLE_NAME = os.environ['REPLICATION_ROLE_NAME']
CLOUDFRONT_LOGS_BUCKET_NAME = os.environ['CLOUDFRONT_LOGS_BUCKET_NAME']
LOAD_BALANCER_LOGS_BUCKET_NAME = os.environ['LOAD_BALANCER_LOGS_BUCKET_NAME']
LOG_ARCHIVE_ACCOUNT_iD = os.environ['LOG_ARCHIVE_ACCOUNT_iD']

sts_client = boto3.client('sts')


def lambda_handler(data, _context):
    region = data['region']
    account_id = data['account_id']
    source_bucket_name = data['bucket_name']
    verdict = data['verdict']
    destination_bucket_name = CLOUDFRONT_LOGS_BUCKET_NAME if verdict == 'cloudfront' else LOAD_BALANCER_LOGS_BUCKET_NAME

    client = get_client('s3', account_id, region)

    print("Enabling encyption of {source_bucket_name}...")
    response = client.put_bucket_encryption(
        Bucket=source_bucket_name,
        ServerSideEncryptionConfiguration={
            'Rules': [
                {
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'AES256'
                    }
                },
            ]
        }
    )
    print(response)

    print("Enabling versioning...")
    response = client.put_bucket_versioning(
        Bucket=source_bucket_name,
        VersioningConfiguration={
            'MFADelete': 'Disabled',
            'Status': 'Enabled'
        }
    )
    print(response)

    print(f"Enabling replication to {destination_bucket_name}...")
    response = client.put_bucket_replication(
        Bucket=source_bucket_name,
        ReplicationConfiguration={
            'Role': f'arn:aws:iam::{account_id}:role/{REPLICATION_ROLE_NAME}',
            'Rules': [
                {
                    'Status': 'Enabled',
                    'Priority': 1,
                    "Filter": {},
                    'DeleteMarkerReplication': {
                        'Status': 'Disabled'
                    },
                    'Destination': {
                        'Account': LOG_ARCHIVE_ACCOUNT_iD,
                        'Bucket': f'arn:aws:s3:::{destination_bucket_name}',
                        'StorageClass': 'STANDARD_IA',
                        'AccessControlTranslation': {
                            'Owner': 'Destination'
                        },
                    },
                },
            ],
        },
    )
    print(response)

    print(f"Setting lifecycle policy...")
    response = client.put_bucket_lifecycle_configuration(
        Bucket=source_bucket_name,
        LifecycleConfiguration={
            'Rules': [
                {
                    'Status': 'Enabled',
                    'Filter': {},
                    'Transitions': [],
                    'Expiration': {
                        'Days': 14,
                    },
                },
            ],
        },
    )
    print(response)

    return True


def get_client(client_type, account_id, region, role=CROSS_ACCOUNT_ROLE):
    other_session = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role}",
        RoleSessionName=f"activate_replication_{account_id}"
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

