import os
import json
import datetime
from datetime import datetime, timezone
import uuid
import boto3

CROSS_ACCOUNT_ROLE = os.environ['CROSS_ACCOUNT_ROLE']

sts_client = boto3.client('sts')

def lambda_handler(data, _context):
    region = data['region']
    account_id = data['account_id']
    bucket_name = data['bucket_name']
    verdict = data['verdict']
    log_type = 'CloudFront' if verdict == 'cloudfront' else 'Load Balancer'

    namespace = 'log-file-aggregation'
    ticket_destination = 'TEAM'
    incident_domain = "INFRA"

    severity = 'INFORMATIONAL'

    title = f"{log_type} log bucket '{bucket_name}' detected"

    description = f'''\
{severity} INCIDENT in account {account_id}, region {region}:

The bucket '{bucket_name}' has been identified as a {log_type} log bucket.

The bucket has been set to replicate any new items to the appropriate bucket in the Log Archive account.
Log files are expired locally after 14 days, but are archived in the Log Archive account should they be 
needed.
'''

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    finding_id = str(uuid.uuid4())
    finding_arn = f"arn:aws:securityhub:{region}:{account_id}:product/{account_id}/default/{finding_id}"

    remediation_text = 'You may want to change the local log file retention time from 14 days to some other value.'
    remediation_url = 'https://docs.aws.amazon.com/AmazonS3/latest/userguide/how-to-set-lifecycle-configuration-intro.html'

    finding = {
        "SchemaVersion": "2018-10-08",
        "Id": finding_id,
        "ProductArn": f"arn:aws:securityhub:{region}:{account_id}:product/{account_id}/default",
        "GeneratorId": title,
        "AwsAccountId": account_id,
        "Types": [
            f"Software and Configuration Checks/SOAR Incidents/{namespace}",
        ],
        "CreatedAt": timestamp,
        "UpdatedAt": timestamp,
        "Severity": {
            "Label": severity
        },
        "Title": title,
        "Description": description,
        "Remediation": {
            "Recommendation": {
                "Text": remediation_text,
                "Url": remediation_url
            }
        },
        "Resources": [
            {
                "Type": "AwsAccountId",
                "Id": account_id,
                "Region": region,
            },
        ],
        "ProductFields": {
            "aws/securityhub/FindingId": finding_arn,
            "aws/securityhub/ProductName": "Default",
            "aws/securityhub/CompanyName": "SOAR Incidents",
            "TicketDestination": ticket_destination,
            "IncidentDomain": incident_domain
        },
        "VerificationState": "TRUE_POSITIVE",
        "Workflow": {
            "Status": "NEW"
        },
        "RecordState": "ACTIVE"
    }

    print(f"Creating {severity} incident for {incident_domain} incident '{title}'")

    client = get_client('securityhub', account_id, region)
    response = client.batch_import_findings(Findings=[finding])
    print(response)

    http_status = response['ResponseMetadata']['HTTPStatusCode']
    if http_status != 200:
        return reply(http_status, message="Failed to import the ASFF finding.")
    if response['FailedCount'] != 0:
        return reply(400, message="Failed to import the ASFF finding.")

    return reply(200, body={"finding": finding})


def reply(status_code, body={}, message=None):
    if message:
        body['message'] = message
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body)
    }


def get_client(client_type, account_id, region, role=CROSS_ACCOUNT_ROLE):
    other_session = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role}",
        RoleSessionName=f"cross_acct_lambda_session_{account_id}"
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
