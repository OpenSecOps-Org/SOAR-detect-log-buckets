#!/usr/bin/env python3

import os
import sys
import subprocess
import toml
import json
import boto3
import re
import botocore
from botocore.exceptions import ClientError
from botocore.exceptions import WaiterError
import time


# Create an STS client
sts_client = boto3.client('sts')


# ---------------------------------------------------------------------------------------
# 
# Common
# 
# ---------------------------------------------------------------------------------------

# Define colors
YELLOW = "\033[93m"
LIGHT_BLUE = "\033[94m"
GREEN = "\033[92m"
RED = "\033[91m"
END = "\033[0m"
BOLD = "\033[1m"

def printc(color, string, **kwargs):
    print(f"{color}{string}{END}", **kwargs)


def load_toml(toml_file):
    # Load the TOML file
    try:
        config = toml.load(toml_file)
    except Exception as e:
        printc(RED, f"Error loading {toml_file}: {str(e)}")
        return None

    return config


def get_account_data_from_toml(account_key, id_or_profile):
    toml_file = '../Delegat-Install/config-accounts.toml'
    # Load the TOML file
    config = load_toml(toml_file)

    # Get the AWS SSO profile or id
    try:
        data = config[account_key][id_or_profile]
    except KeyError:
        printc(RED, f"Error: '{account_key}' account not found in {toml_file}")
        return None

    return data


def get_all_parameters(delegat_app):
    toml_file = f'../Delegat-Install/config-{delegat_app}.toml'
    # Load and return the whole TOML file
    config = load_toml(toml_file)
    return config


def parameters_to_sam_string(params, repo_name):
    section = params[repo_name]['SAM']
    params_list = []
    for k, v in section.items():
        v = dereference(v, params)
        params_list.append(f'{k}="{v}"')
    return ' '.join(params_list)


def parameters_to_cloudformation_json(params, repo_name, template_name):
    section = params[repo_name][template_name]
    cf_params = []
    for k, v in section.items():
        v = dereference(v, params)
        cf_params.append({
            'ParameterKey': k,
            'ParameterValue': v
        })
    return cf_params


def dereference(value, params):
    # Check if value is exactly '{all-regions}'
    if value == '{all-regions}':
        # Get main region and other regions
        main_region = params.get('main-region', '')
        other_regions = params.get('other-regions', [])
        
        # Add main region as a new first element
        all_regions = [main_region] + other_regions

        # Return a list of strings
        return all_regions

    # Check if value contains a reference
    elif "{" in value and "}" in value:
        def substitute(m):
            param = m.group(1)
            if param in params:
                return params[param]
            else:
                # If not found in params, try to get account data from TOML
                account_data = get_account_data_from_toml(param, 'id')
                if account_data is not None:
                    return account_data
                else:
                    raise ValueError(f"Parameter {param} not found")

        # Replace any string enclosed in braces with the corresponding parameter
        value = re.sub(r'\{(.+?)\}', substitute, value)

    return value

# ---------------------------------------------------------------------------------------
# 
# SAM
# 
# ---------------------------------------------------------------------------------------

def process_sam(sam, repo_name, params):
    printc(LIGHT_BLUE, f"")
    printc(LIGHT_BLUE, f"")
    printc(LIGHT_BLUE, "================================================")
    printc(LIGHT_BLUE, f"")
    printc(LIGHT_BLUE, f"  SAM")
    printc(LIGHT_BLUE, f"")
    printc(LIGHT_BLUE, "------------------------------------------------")
    printc(LIGHT_BLUE, f"")

    sam_account = sam['profile']
    sam_regions = dereference(sam['regions'], params)

    stack_name = sam['stack-name']
    capabilities = sam.get('capabilities', 'CAPABILITY_IAM')
    s3_prefix = sam['s3-prefix']
    tags = 'infra:immutable="true"'

    # Get the AWS SSO profile
    sam_profile = get_account_data_from_toml(sam_account, 'profile')

    # Get the SAM parameter overrides
    sam_parameter_overrides = parameters_to_sam_string(params, repo_name)
    print()
    print(sam_parameter_overrides)

    try:
        printc(LIGHT_BLUE, "Executing 'git pull'...")
        subprocess.run(['git', 'pull'], check=True)

        printc(LIGHT_BLUE, "Executing 'sam build'...")
        subprocess.run(['sam', 'build'], check=True)

        for region in sam_regions:
            printc(LIGHT_BLUE, f"")
            printc(LIGHT_BLUE, f"")
            printc(LIGHT_BLUE, "================================================")
            printc(LIGHT_BLUE, f"")
            printc(LIGHT_BLUE, f"  Deploying to {region}...")
            printc(LIGHT_BLUE, f"")
            printc(LIGHT_BLUE, "------------------------------------------------")
            printc(LIGHT_BLUE, f"")

            printc(LIGHT_BLUE, "Executing 'sam deploy'...")
            subprocess.run(
                [
                    'sam', 'deploy', 
                    '--stack-name', stack_name,
                    '--capabilities', capabilities,
                    '--resolve-s3',
                    '--region', region,
                    '--profile', sam_profile, 
                    '--parameter-overrides', sam_parameter_overrides,
                    '--s3-prefix', s3_prefix,
                    '--tags', tags,
                    #  '--no-execute-changeset', 
                    '--no-confirm-changeset', 
                    '--no-disable-rollback',
                    '--no-fail-on-empty-changeset', 
                ],
                check=True)

            printc(GREEN, "")
            printc(GREEN + BOLD, "Deployment completed successfully.")

    except subprocess.CalledProcessError as e:
        printc(RED, f"An error occurred while executing the command: {str(e)}")

    printc(GREEN, "")


# ---------------------------------------------------------------------------------------
# 
# CloudFormation
# 
# ---------------------------------------------------------------------------------------

# Function to get a client for the specified service, account, and region
def get_client(client_type, account_id, region, role):
    # Assume the specified role in the specified account
    other_session = sts_client.assume_role(
        RoleArn=f"arn:aws:iam::{account_id}:role/{role}",
        RoleSessionName=f"deploy_cloudformation_{account_id}"
    )
    access_key = other_session['Credentials']['AccessKeyId']
    secret_key = other_session['Credentials']['SecretAccessKey']
    session_token = other_session['Credentials']['SessionToken']
    # Create a client using the assumed role credentials and specified region
    return boto3.client(
        client_type,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        aws_session_token=session_token,
        region_name=region
    )


def does_stack_exist(stack_name, account_id, region, role):
    try:
        # Get CloudFormation client for the specified account and region
        cf_client = get_client("cloudformation", account_id, region, role)
        
        # Describe the stack using the provided name
        cf_client.describe_stacks(StackName=stack_name)
        
        # If no exception is raised, the stack exists
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'ValidationError' and 'does not exist' in e.response['Error']['Message']:
            return False
        else:
            raise e


def does_stackset_exist(stackset_name, account_id, region, role):
    try:
        # Get CloudFormation client for the specified account and region
        cf_client = get_client("cloudformation", account_id, region, role)
        
        # Describe the stack set using the provided name
        cf_client.describe_stack_set(StackSetName=stackset_name)
        
        # If no exception is raised, the stack set exists
        return True
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'StackSetNotFoundException':
            return False
        else:
            raise e


def read_cloudformation_template(path):
    """
    Reads the CloudFormation template from the specified path and checks for size constraints.
    
    Parameters:
    - path (str): Path to the CloudFormation template file.
    
    Returns:
    - template (str): Contents of the CloudFormation template file.
    
    Raises:
    - Exception if the file is missing or exceeds the size limit.
    """
    
    try:
        # Read the file content
        with open(path, 'r') as file:
            template = file.read()
            
        # Check for size constraints
        if len(template.encode('utf-8')) > 51200:  # CloudFormation string template size limit is 51,200 bytes
            raise Exception("The CloudFormation template exceeds the maximum size limit of 51,200 bytes.")
        
        return template
    
    except FileNotFoundError:
        raise Exception(f"The specified CloudFormation template at path '{path}' was not found.")


def update_stack(stack_name, template_body, parameters, capabilities, account_id, region, role):
    """
    Update an existing AWS CloudFormation stack using the provided template and parameters.
    
    Parameters:
    - stack_name (str): Name of the CloudFormation stack to update.
    - template_body (str): CloudFormation template as a string.
    - parameters (list): List of parameters to override in the stack.   
    - capabilities (str): CloudFormation capabilities
    - account_id (str): AWS Account ID to assume the role from.
    - region (str): AWS Region where the stack resides.
    - role (str): IAM Role to assume for cross-account access.
    
    Returns:
    - response (dict): Response from the CloudFormation API.
    """
    
    # Get the CloudFormation client using the get_client function
    cf_client = get_client('cloudformation', account_id, region, role)

    # Standard tags
    tags = [
        {
            'Key': 'infra:immutable',
            'Value': 'true'
        }
    ]

    try:
        # Update the stack
        response = cf_client.update_stack(
            StackName=stack_name,
            TemplateBody=template_body,
            Parameters=parameters,
            Capabilities=[capabilities],
            Tags=tags,
        )
        return True
    except botocore.exceptions.ClientError as e:
        if "No updates are to be performed" in str(e):
            printc(GREEN, "Infrastructure will not change. Skipping update.")
            return False
        else:
            raise e
        

def create_stack(stack_name, template_body, parameters, capabilities, account_id, region, role):
    """
    Create a new AWS CloudFormation stack using the provided template and parameters.
    
    Parameters:
    - stack_name (str): Name of the CloudFormation stack to update.
    - template_body (str): CloudFormation template as a string.
    - parameters (list): List of parameters to override in the stack.   
    - capabilities (str): CloudFormation capabilities
    - account_id (str): AWS Account ID to assume the role from.
    - region (str): AWS Region where the stack resides.
    - role (str): IAM Role to assume for cross-account access.
    
    Returns:
    - response (dict): Response from the CloudFormation API.
    """
    
    # Get the CloudFormation client using the get_client function
    cf_client = get_client('cloudformation', account_id, region, role)

    # Standard tags
    tags = [
        {
            'Key': 'infra:immutable',
            'Value': 'true'
        }
    ]

    try:
        # Update the stack
        response = cf_client.create_stack(
            StackName=stack_name,
            TemplateBody=template_body,
            Parameters=parameters,
            Capabilities=[capabilities],
            Tags=tags,
        )
        return True
    except botocore.exceptions.ClientError as e:
        if "No updates are to be performed" in str(e):
            printc(GREEN, "Infrastructure will not change. Skipping update.")
            return False
        else:
            raise e
        

def update_stack_set(stack_set_name, template_body, parameters, capabilities, account_id, region, role):
    """
    Update an existing AWS CloudFormation StackSet using the provided template and parameters.
    
    Parameters:
    - stack_set_name (str): Name of the StackSet to update.
    - template_body (str): CloudFormation template as a string.
    - parameters (list): List of parameters to override in the StackSet.
    - capabilities (str): CloudFormation capabilities.
    - account_id (str): AWS Account ID to assume the role from.
    - region (str): AWS Region where the StackSet resides.
    - role (str): IAM Role to assume for cross-account access.
    
    Returns:
    - response (dict): Response from the CloudFormation API.
    """
    
    # Get the CloudFormation client using the get_client function
    cf_client = get_client('cloudformation', account_id, region, role)

    # Standard tags
    tags = [
        {
            'Key': 'infra:immutable',
            'Value': 'true'
        }
    ]

    try:
        # Update the StackSet
        response = cf_client.update_stack_set(
            StackSetName=stack_set_name,
            TemplateBody=template_body,
            Parameters=parameters,
            Capabilities=[capabilities],
            Tags=tags,
        )
        return True
    except botocore.exceptions.ClientError as e:
        if "No updates are to be performed" in str(e):
            print("StackSet update: No changes are needed.")
            return False
        else:
            raise e


def create_stack_set(stack_set_name, template_body, parameters, capabilities, root_ou, deployment_regions, account_id, region, role):
    cf_client = get_client('cloudformation', account_id, region, role)

    tags = [
        {
            'Key': 'infra:immutable',
            'Value': 'true'
        }
    ]

    try:
        response = cf_client.create_stack_set(
            StackSetName=stack_set_name,
            TemplateBody=template_body,
            Parameters=parameters,
            Capabilities=[capabilities],
            PermissionModel='SERVICE_MANAGED',
            AutoDeployment={
                'Enabled': True,
                'RetainStacksOnAccountRemoval': False
            },
            Tags=tags,
        )

        monitor_stack_until_complete(stack_set_name, account_id, region, role)

        cf_client.create_stack_instances(
            StackSetName=stack_set_name,
            DeploymentTargets={
                'OrganizationalUnitIds': [root_ou],
            },
            Regions=[deployment_regions],
            OperationPreferences={
                'FailureTolerancePercentage': 0,
                'MaxConcurrentPercentage': 100
            },
        )
        monitor_stack_until_complete(stack_set_name, account_id, region, role)

        return response
    except botocore.exceptions.ClientError as e:
        if "AlreadyExistsException" in str(e):
            print("StackSet already exists.")
        else:
            raise e


def monitor_stack_until_complete(stack_name, account_id, region, role):
    """
    Polls the specified CloudFormation stack until it reaches a terminal state.
    
    Parameters:
    - stack_name (str): Name of the CloudFormation stack to monitor.
    - account_id (str): AWS Account ID to assume the role from.
    - region (str): AWS Region where the stack resides.
    - role (str): IAM Role to assume for cross-account access.
    """
    
    # Get the CloudFormation client using the get_client function
    cf_client = get_client('cloudformation', account_id, region, role)
    
    # Define terminal states for CloudFormation stacks
    terminal_states = ["CREATE_COMPLETE", "ROLLBACK_COMPLETE", "UPDATE_COMPLETE", "UPDATE_ROLLBACK_COMPLETE", "DELETE_COMPLETE"]
    
    while True:
        try:
            # Get the current stack status
            stack = cf_client.describe_stacks(StackName=stack_name)
            stack_status = stack['Stacks'][0]['StackStatus']
            
            # Print the stack status with the appropriate color and reset the color afterward
            if "ROLLBACK" in stack_status or "DELETE" in stack_status:
                print(f"{RED}\rStack Status: {stack_status}          {END}", end="")
            elif "CREATE_COMPLETE" in stack_status or "UPDATE_COMPLETE" in stack_status:
                print(f"{GREEN}\rStack Status: {stack_status}          {END}", end="")
            else:
                print(f"{LIGHT_BLUE}\rStack Status: {stack_status}          {END}", end="")
            
            # Exit loop if the stack is in a terminal state
            if stack_status in terminal_states:
                print()  # Move to the next line after final state is reached
                time.sleep(5)
                break
            
            # Sleep for a shorter interval before checking again
            time.sleep(1)  # Shorter interval for more frequent checks
        except botocore.exceptions.WaiterError as ex:
            if ex.last_response.get('Error', {}).get('Code') == 'ThrottlingException':
                print("API rate limit exceeded. Retrying in 5 seconds...")
                time.sleep(5)
            else:
                raise
        except botocore.exceptions.OperationInProgressException as op_in_prog_ex:
            print(f"Another operation is in progress: {op_in_prog_ex}")
            print("Retrying in 30 seconds...")
            time.sleep(30)


def process_cloudformation(jobs, repo_name, params, cross_account_role):
    if not jobs:
        return
    
    printc(LIGHT_BLUE, f"")
    printc(LIGHT_BLUE, f"")
    printc(LIGHT_BLUE, "================================================")
    printc(LIGHT_BLUE, f"")
    printc(LIGHT_BLUE, f"  CloudFormation")
    printc(LIGHT_BLUE, f"")
    printc(LIGHT_BLUE, "------------------------------------------------")
    printc(LIGHT_BLUE, f"")

    admin_account_id = get_account_data_from_toml('admin-account', 'id')
    #org_id = params['org-id']
    root_ou = params['root-ou']
    main_region = params['main-region']

    for job in jobs:
        stack_name = job.get('name')
        template_path = job.get('template')
        account = dereference(job.get('account'), params)
        regions = dereference(job.get('regions'), params)
        capabilities = job.get('capabilities', 'CAPABILITY_IAM')

        if isinstance(regions, str):
            regions = [regions]

        print()

        stack_set = False
        if account == 'ALL':
            stack_set = True
            account = admin_account_id
            printc(YELLOW, "STACK SET --------------------------------")
        else:
            printc(YELLOW, "STACK ------------------------------------")

        printc(YELLOW, stack_name)
        printc(YELLOW, template_path)
        printc(YELLOW, account)
        printc(YELLOW, regions)
        printc(YELLOW, capabilities)

        template_str = read_cloudformation_template(template_path)
        stack_parameters = parameters_to_cloudformation_json(params, repo_name, stack_name)

        if not stack_set:
            for region in regions:
                exists = does_stack_exist(stack_name, account, region, cross_account_role)
                if exists:
                    printc(YELLOW, f"- Stack exists in {account} and {region}")
                    monitor_stack_until_complete(stack_name, account, region, cross_account_role)
                    changing = update_stack(stack_name, template_str, stack_parameters, capabilities, account, region, cross_account_role)
                    if changing:
                        time.sleep(1)
                        monitor_stack_until_complete(stack_name, account, region, cross_account_role)
                else:
                    printc(YELLOW, f"- Stack does not exist in {account} and {region}")
                    changing = create_stack(stack_name, template_str, stack_parameters, capabilities, account, region, cross_account_role)
                    if changing:
                        time.sleep(1)
                        monitor_stack_until_complete(stack_name, account, region, cross_account_role)

        else:
            exists = does_stackset_exist(stack_name, account, main_region, cross_account_role)
            if exists:
                printc(YELLOW, f"- StackSet exists in {account} and {main_region}")
                monitor_stack_until_complete(stack_name, account, main_region, cross_account_role)
                changing = update_stack_set(stack_name, template_str, stack_parameters, capabilities, account, main_region, cross_account_role)
                if changing:
                    time.sleep(1)
                    monitor_stack_until_complete(stack_name, account, main_region, cross_account_role)
            else:
                printc(YELLOW, f"- StackSet does not exist in {account} and {main_region}")
                create_stack_set(stack_name, template_str, stack_parameters, capabilities, root_ou, regions, account, main_region, cross_account_role)

            # Check the Stack(s) in the admin account(s) as well
            for region in regions:
                exists = does_stack_exist(stack_name, admin_account_id, region, cross_account_role)
                if exists:
                    printc(YELLOW, f"- Also deployed as a single Stack in the AWS Organization admin account in {region}")
                    monitor_stack_until_complete(stack_name, account, region, cross_account_role)
                    changing = update_stack(stack_name, template_str, stack_parameters, capabilities, account, region, cross_account_role)
                    if changing:
                        time.sleep(1)
                        monitor_stack_until_complete(stack_name, account, region, cross_account_role)
                else:
                    printc(YELLOW, f"- Not deployed as a single Stack in the AWS Organization admin account in {region}")
                    changing = create_stack(stack_name, template_str, stack_parameters, capabilities, account, region, cross_account_role)
                    if changing:
                        time.sleep(1)
                        monitor_stack_until_complete(stack_name, account, region, cross_account_role)


# ---------------------------------------------------------------------------------------
# 
# Entry point
# 
# ---------------------------------------------------------------------------------------

def deploy():
    # Check if 'config-deploy.toml' exists at the root of the repo
    if not os.path.exists('config-deploy.toml'):
        printc(RED, "Error: 'config-deploy.toml' is missing.")
        printc(YELLOW, "Please create 'config-deploy.toml'.")
        return
    
    # Get the deployment configuration
    dpcf = load_toml('config-deploy.toml')
    delegat_app = dpcf['part-of']
    repo_name = dpcf['repo-name']

    # Get the parameters (all of them, for all repos)
    params = get_all_parameters(delegat_app)
    cross_account_role = params['cross-account-role']
    
    # Get the respective sections
    sam = dpcf.get('SAM')
    pre_sam = dpcf.get('pre-SAM-CloudFormation') or dpcf.get('pre-SAM')
    post_sam = dpcf.get('post-SAM-CloudFormation') or dpcf.get('post-SAM')
    cf = dpcf.get('CloudFormation')

    # Decide what to do
    if sam:
        process_cloudformation(pre_sam, repo_name, params, cross_account_role)
        process_sam(sam, repo_name, params)
        process_cloudformation(post_sam, repo_name, params, cross_account_role)

    else:
        process_cloudformation(cf, repo_name, params, cross_account_role)


def main():
    deploy()


if __name__ == '__main__':
    main()
