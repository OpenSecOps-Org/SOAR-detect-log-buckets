"""
The Lambdas the state machine invokes: throttling and other transient AWS errors leave them as
AWSTransientError, which the state machine retries before its Catch takes over. Before, a throttled S3 call
in Get Latest Files was caught as "Not A Log Bucket", so a log bucket could be silently left unreplicated.
Other errors keep their own name and are not retried.
"""

from unittest.mock import MagicMock, patch

import botocore.exceptions
import pytest

from aws_errors import AWSTransientError
from functions.activate_replication import app as activate_replication
from functions.create_incident import app as create_incident
from functions.get_latest_files import app as get_latest_files

BUCKET = {'region': 'eu-north-1', 'account_id': '333333333333', 'bucket_name': 'example-bucket',
          'verdict': 'cloudfront'}


def client_error(code, status=400):
    return botocore.exceptions.ClientError(
        {'Error': {'Code': code, 'Message': code}, 'ResponseMetadata': {'HTTPStatusCode': status}}, 'op')


SLOW_DOWN = client_error('SlowDown', 503)
DENIED = client_error('AccessDenied', 403)


def run(module, client=None, resource=None):
    patches = [patch.object(module, 'get_client', return_value=client or MagicMock())]
    if hasattr(module, 'get_resource'):
        patches.append(patch.object(module, 'get_resource', return_value=resource or MagicMock()))
    for p in patches:
        p.start()
    try:
        return module.lambda_handler(dict(BUCKET), None)
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------------------

def test_lists_the_latest_files():
    resource = MagicMock()
    obj = MagicMock(key='a.log', last_modified=1)
    resource.Bucket.return_value.objects.filter.return_value = [obj]
    assert run(get_latest_files, resource=resource) == ['a.log']


@pytest.mark.parametrize('error, transient', [(SLOW_DOWN, True), (client_error('InternalError', 500), True),
                                              (DENIED, False)])
def test_get_latest_files_errors(error, transient):
    client = MagicMock()
    client.head_bucket.side_effect = error
    with pytest.raises(AWSTransientError if transient else botocore.exceptions.ClientError) as raised:
        run(get_latest_files, client=client)
    assert isinstance(raised.value, AWSTransientError) == transient


def test_a_throttled_listing_is_retried():
    resource = MagicMock()
    resource.Bucket.return_value.objects.filter.side_effect = SLOW_DOWN
    with pytest.raises(AWSTransientError):
        run(get_latest_files, resource=resource)


def test_a_throttled_role_assumption_is_retried():
    sts = MagicMock()
    sts.assume_role.side_effect = client_error('Throttling')
    with patch.object(get_latest_files, 'sts_client', sts):
        with pytest.raises(AWSTransientError):
            get_latest_files.lambda_handler(dict(BUCKET), None)


# ---------------------------------------------------------------------------

def test_activates_replication():
    client = MagicMock()
    assert run(activate_replication, client=client) is True
    client.put_bucket_replication.assert_called_once()


@pytest.mark.parametrize('call', ['put_bucket_encryption', 'put_bucket_versioning', 'put_bucket_replication',
                                  'put_bucket_lifecycle_configuration'])
@pytest.mark.parametrize('error, transient', [(SLOW_DOWN, True), (DENIED, False)])
def test_activate_replication_errors(call, error, transient):
    client = MagicMock()
    getattr(client, call).side_effect = error
    with pytest.raises(AWSTransientError if transient else botocore.exceptions.ClientError) as raised:
        run(activate_replication, client=client)
    assert isinstance(raised.value, AWSTransientError) == transient


# ---------------------------------------------------------------------------

def test_creates_the_incident():
    client = MagicMock()
    client.batch_import_findings.return_value = {'ResponseMetadata': {'HTTPStatusCode': 200}, 'FailedCount': 0}
    assert run(create_incident, client=client)['statusCode'] == 200


@pytest.mark.parametrize('error, transient', [(client_error('TooManyRequestsException', 429), True),
                                              (client_error('LimitExceededException', 429), True),
                                              (client_error('InvalidAccessException', 401), False)])
def test_create_incident_errors(error, transient):
    client = MagicMock()
    client.batch_import_findings.side_effect = error
    with pytest.raises(AWSTransientError if transient else botocore.exceptions.ClientError) as raised:
        run(create_incident, client=client)
    assert isinstance(raised.value, AWSTransientError) == transient
