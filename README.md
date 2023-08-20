# SOAR-detect-log-buckets

Whenever a bucket is created, we want to detect whether it contains log files
from CloudFront or AWS Elastic Load Balancing. If so, we replicate the contents
of such buckets to the Log Archive account.

The implementation is based on all member accounts passing the CreateBucket and
DeleteBucket events to the custom event bus `security-hub-automation` in the 
organisation account.

To make the accounts forward this event:

1. Deploy `log-archive-buckets.yaml` in the Log Archive account. This creates the
   buckets for aggregation of CloudFront and load balancer logs, with the 
   appropriate cross-account configuration.

2. Deploy `s3-log-replication-source-account-role.yaml` to the org account in your
   main region, then as a StackSet to all accounts, likewise in your main region only.
   This creates the IAM Role replication will use. It has permissions to replicate
   to the aggregation buckets in the Log Archive account.

3. Deploy `detect-bucket-lifecycle.yaml` to the org account in each supported region, 
   then as a StackSet to all accounts and all supported regions. This sets up
   an EventBridge rule in each account to transfer S3 bucket lifecycle events to the
   Organisation account from which detection will take place.

3. Then deploy this SAM project in the organisation account, in each supported 
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

First log in to your AWS organisation using SSO. Obtain AWSAdministratorAccess for the AWS Organizations 
admin account. Paste the credentials into the terminal. Then type:

```console
./deploy
```
