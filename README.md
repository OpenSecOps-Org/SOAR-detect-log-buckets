# SOAR-detect-log-buckets

Whenever a bucket is created, we want to detect whether it contains log files
from CloudFront or AWS Elastic Load Balancing. If so, we replicate the contents
of such buckets to the Log Archive account.

The implementation is based on all member accounts passing the CreateBucket and
DeleteBucket events to the custom event bus `SOAR-events` in the 
organisation account.

The `./deploy` command does the following:

1. It deploys `log-archive-buckets.yaml` in the Log Archive account. This creates the
   buckets for aggregation of CloudFront and load balancer logs, with the 
   appropriate cross-account configuration.

2. It deploys `s3-log-replication-source-account-role.yaml` to the org account in your
   main region, then as a StackSet to all accounts, likewise in your main region only.
   This creates the IAM Role replication will use. It has permissions to replicate
   to the aggregation buckets in the Log Archive account.

3. It deploys `detect-bucket-lifecycle.yaml` to the org account in each supported region, 
   then as a StackSet to all accounts and all supported regions. This sets up
   an EventBridge rule in each account to transfer S3 bucket lifecycle events to the
   Organisation account from which detection will take place.

3. It then deploys this SAM project in the organisation account, in each supported 
   region. This installs everything necessary to detect S3 log buckets and set up
   replication as appropriate.

When this has been done, new buckets will be monitored for a maximum of two days.
Whenever the system detects that the new bucket contains files with names conforming
to the log name formats for CloudFront or Elastic Load Balancing, the bucket will be
set up to replicate new contents to the centralised aggregation buckets in the Log
Archive account. The bucket may contain up to 5 non-log files; a decision will be
made only when enough files have been detected. The decision is made on the 10 last
files to be put in the bucket.


## Deployment

First make sure that your SSO setup is configured with a default profile giving you AWSAdministratorAccess
to your AWS Organizations administrative account. This is necessary as the AWS cross-account role used 
during deployment only can be assumed from that account.

```console
aws sso login
```

Then type:

```console
./deploy
```
