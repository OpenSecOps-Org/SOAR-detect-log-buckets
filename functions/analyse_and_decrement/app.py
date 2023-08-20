import re


def lambda_handler(data, _context):
    files = data['files']
    verdict = 'undecided'

    cloudfront_logs = 0
    elb_logs = 0
    other_files = 0

    p_cf = re.compile('.+[A-Z0-9]{8,}\.\d{4}-\d{2}-\d{2}-\d{2}\.[A-Z0-9]{8,}\.gz$')
    p_elb = re.compile('.*ELBAccessLogTestFile$|.*AWSLogs.+elasticloadbalancing.+\.log\.gz$')

    for file in files:
        if p_cf.match(file):
            cloudfront_logs += 1
        elif p_elb.match(file):
            elb_logs += 1
        else:
            other_files += 1
            
    if cloudfront_logs > 0 and elb_logs > 0:
        verdict = 'unusable'
    elif cloudfront_logs == 0 and elb_logs == 0 and other_files > 5:
        verdict = 'unusable'
    elif cloudfront_logs > 0 and other_files < cloudfront_logs:
        verdict = 'cloudfront'
    elif elb_logs > 0 and other_files < elb_logs:
        verdict = 'elb'

    data['verdict'] = verdict
    data['counter'] -= 1
    data['cloudfront_logs'] = cloudfront_logs
    data['elb_logs'] = elb_logs
    data['other_files'] = other_files
    return data

