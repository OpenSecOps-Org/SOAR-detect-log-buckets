# Change Log

## v1.3.2
    * Enable auto-close workflow for external pull requests, enforcing the cathedral governance policy uniformly across all OpenSecOps repositories. Pull requests from non-team authors are closed automatically with a redirect comment pointing to the bug-report template, the GitHub Security Advisory flow, and the fork-under-MPL-2.0 path.
    * `SECURITY.md` §14 now carries a Trust-page cross-link ([opensecops.org/trust.html](https://www.opensecops.org/trust.html)) alongside the existing canonical supply-chain document link, positioning the Trust page as the lighter customer-facing synthesis.

## v1.3.1

- `SECURITY.md` and `README` updated re: OpenSSF Scorecard publication status. See [supply-chain documentation](https://github.com/OpenSecOps-Org/Documentation/blob/main/docs/security/supply-chain.md) §5.5.

## v1.3.0
    * Converted to OpenSecOps supply-chain framework: hash-pinned dependencies, signed releases, daily CVE scan, Scorecard. See `SECURITY.md`.
    * `boto3` pinned to `1.42.94` (was `1.28.33`) per project-wide pin policy.

## v1.2.9
    * Updated GitHub remote references in publish.zsh script to use only OpenSecOps-Org, removed Delegat-AB

## v1.2.8
    * Updated GitHub organization name from CloudSecOps-Org to OpenSecOps-Org.
    * Updated references to CloudSecOps-Installer to Installer.

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
