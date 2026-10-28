import os
import sys
from unittest.mock import MagicMock, patch

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)
# The Lambdas import aws_errors from their layer, as they do in AWS
sys.path.insert(0, os.path.join(ROOT, 'functions', 'layers', 'aws_errors', 'python'))

# Module-level boto3 clients are created at import; no call is made, but a region is needed
os.environ.setdefault('AWS_DEFAULT_REGION', 'eu-north-1')
os.environ.setdefault('CROSS_ACCOUNT_ROLE', 'AWSControlTowerExecution')
os.environ.setdefault('REPLICATION_ROLE_NAME', 'example-replication-role')
os.environ.setdefault('CLOUDFRONT_LOGS_BUCKET_NAME', 'example-cloudfront-logs')
os.environ.setdefault('LOAD_BALANCER_LOGS_BUCKET_NAME', 'example-load-balancer-logs')
os.environ.setdefault('LOG_ARCHIVE_ACCOUNT_iD', '222222222222')
os.environ.setdefault('LOG_ARCHIVE_ACCOUNT_ID', '222222222222')
os.environ.setdefault('STATE_MACHINE_ARN', 'arn:aws:states:eu-north-1:111111111111:stateMachine:example')


@pytest.fixture(autouse=True)
def mock_aws_services():
    """Prevents ALL AWS API calls: every boto3 client and resource the Lambdas create is a MagicMock."""
    with patch('boto3.client', side_effect=lambda *args, **kwargs: MagicMock(name=f'client:{args[0]}')), \
            patch('boto3.resource', side_effect=lambda *args, **kwargs: MagicMock(name=f'resource:{args[0]}')):
        yield
