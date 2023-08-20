#!/usr/bin/env python3

import os
import sys
import subprocess
import toml
import json
import boto3

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



def get_account_data_from_toml(account_key, id_or_profile, toml_file='config-accounts.toml'):
    # Load the TOML file
    config = load_toml(toml_file)

    # Get the AWS SSO profile or id
    try:
        data = config[id_or_profile][account_key]
    except KeyError:
        printc(RED, f"Error: '{account_key}' account not found in {toml_file}")
        return None

    return data


def get_global_parameters(repo, toml_file='../Delegat-Install/config-soar.toml'):
    # Load the TOML file
    config = load_toml(toml_file)

    # Get the global parameters for the given repo
    try:
        data = config[repo]
    except KeyError:
        printc(RED, f"Error: '{repo}' not found in {toml_file}")
        return None

    return data


def parameters_to_string(params):
    string = ', '.join(f'{k}="{v}"' for k, v in params.items())
    return string


def called_locally():
    printc(GREEN, "Hello, developer.")

    # Check if 'config-accounts.toml' exists at the root of the repo
    if not os.path.exists('config-accounts.toml'):
        printc(RED, "Error: 'config-accounts.toml' does not exist.")
        printc(YELLOW, "Please create 'config-accounts.toml'. Refer to the README for more information.")
        return

    # Get the AWS Organizations 12-digit account ID
    admin_account_id = get_account_data_from_toml('admin-account', 'id')
    # Get the AWS SSO profile
    profile = get_account_data_from_toml('admin-account', 'profile')
    # Get the parameters from the Delegat-Install repo
    gp = get_global_parameters('SOAR-detect-log-buckets')
    parameter_overrides = parameters_to_string(gp)
    # Get the deployment configuration
    dpcf = load_toml('config-deploy.toml')
    print(dpcf)
    stack_name = dpcf['SAM']['stack-name']
    capabilities = dpcf['SAM']['capabilities']
    s3_prefix = dpcf['SAM']['s3-prefix']
    regions = dpcf['SAM']['regions']
    tags = "infra:immutable=\"true\""

    for region in regions:
        printc(LIGHT_BLUE, f"")
        printc(LIGHT_BLUE, f"")
        printc(LIGHT_BLUE, "================================================")
        printc(LIGHT_BLUE, f"")
        printc(LIGHT_BLUE, f"  Deploying to {region}...")
        printc(LIGHT_BLUE, f"")
        printc(LIGHT_BLUE, "------------------------------------------------")
        printc(LIGHT_BLUE, f"")

        try:
            printc(LIGHT_BLUE, "Executing 'git pull'...")
            subprocess.run(['git', 'pull'], check=True)

            printc(LIGHT_BLUE, "Executing 'sam build'...")
            subprocess.run(['sam', 'build'], check=True)

            printc(LIGHT_BLUE, "Executing 'sam deploy'...")
            subprocess.run(
                [
                    'sam', 'deploy', 
                    '--stack-name', stack_name,
                    '--capabilities', capabilities,
                    '--resolve-s3',
                    '--region', region,
                    '--profile', profile, 
                    '--parameter-overrides', '',
                    '--s3-prefix', s3_prefix,
                    '--tags', tags,
                  #  '--no-execute-changeset', 
                    '--no-confirm-changeset', 
                    '--no-disable-rollback',
                    '--no-fail-on-empty-changeset', 
                ],
                check=True)

            printc(GREEN, "Deployment completed successfully.")
        except subprocess.CalledProcessError as e:
            printc(RED, f"An error occurred while executing the command: {str(e)}")


def called_from_installer(accounts_file, config_file):
    printc(GREEN, f"Called from Delegat Installer with accounts file: {accounts_file} and config file: {config_file}")
    # TODO: Implement the function here


def main():
    # Check if the script was called with additional parameters
    if len(sys.argv) > 1:
        accounts_file = sys.argv[1]
        config_file = sys.argv[2]
        called_from_installer(accounts_file, config_file)
    else:
        called_locally()

if __name__ == '__main__':
    main()

