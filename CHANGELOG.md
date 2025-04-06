# Change Log

## v1.2.7
    * File paths corrected for the new name of the installer.

## v1.2.6
    * Updated LICENSE file to MPL 2.0.

## v1.2.5
    * Updated publish.zsh to support dual-remote publishing to CloudSecOps-Org repositories.

## v1.2.4
    * Python v3.12.2.
    * `.python-version` file to support `pyenv`.

## v1.2.3
    * Changed incident level to MEDIUM for the lifecycle lambda.

## v1.2.2
    * Fixed DescribeExecution permissions.

## v1.2.1
    * Using describe_execution to get the input.

## v1.2.0
    * Now handling the edge case of buckets being created, deleted, and then created again within 90 days.

## v1.1.5
    * Switched to storage class STANDARD rather than STANDARDIA, for auto-construction of storage dashboards.

## v1.1.4
    * Refreshed scripts.

## v1.1.3
    * Open-source credits and URLs
    * Fixed installer initial stackset creation.

## v1.1.2
    * `--dry-run` and `--verbose` added to `deploy`.

## v1.1.1
* Better formatting and colourisation.

## v1.1.0
* CloudFormation support via `config-deploy.toml`.
* Deployable Delegat repos (both for Foundation and for SOAR) must now have a `config-deploy.toml` file
  to describe the regions, steps and nature of the deployment.

## v1.0.0
* First release.
