# Security policy

Please report vulnerabilities privately through the repository's security
advisory feature. Do not include credentials, access tokens, bucket names, or
file contents in public issues.

cloudsync stores Google OAuth tokens with owner-only permissions. Prefer AWS
profiles, environment credentials, or workload/IAM roles over CLI secrets.
Review every `cloudsync plan` before enabling `--delete`.
