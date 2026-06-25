# SSO and profiles

After `aws sso login --profile <profile>`, **neither boto3 nor the AWS CLI picks
up the profile automatically**. SSO login refreshes the SSO cache but does not
update the default-profile credential chain.

```bash
export AWS_PROFILE=<profile>          # once per shell
# or prefix individual commands:
AWS_PROFILE=<profile> aws ecs list-clusters
AWS_PROFILE=<profile> python3 -c "import boto3; ..."
```

Without it you get `UnrecognizedClientException: The security token included in
the request is invalid` (CLI) or boto3 silently using the wrong/no credentials.

Applies to **any** AWS access in an SSO-backed account: CLI (`aws ecs …`,
`aws cloudformation …`) and boto3 alike.

If a script must be portable across profiles, accept the profile name as an
argument and construct `boto3.Session(profile_name=...)` explicitly rather than
relying on the ambient `AWS_PROFILE`.
