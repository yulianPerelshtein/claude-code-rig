# AWS SSO profiles with boto3 and the CLI

After `aws sso login --profile <profile>`, **neither boto3 nor the AWS CLI picks
up the profile automatically.** You'll get `UnrecognizedClientException` or an
invalid/expired-token error until you point them at the profile explicitly.

## Fix

Set `AWS_PROFILE` per shell or per command:

```bash
aws sso login --profile my-sso-profile

# Per shell:
export AWS_PROFILE=my-sso-profile
aws sts get-caller-identity        # now resolves

# Or per command:
AWS_PROFILE=my-sso-profile python my_script.py
```

## Notes

- boto3 reads `AWS_PROFILE` the same way the CLI does; with it set, `Session()`
  resolves SSO credentials from the cached login.
- If a script must be portable across profiles, accept the profile name as an
  argument and construct `boto3.Session(profile_name=...)` explicitly rather
  than relying on ambient env.
- SSO tokens expire — re-run `aws sso login` when calls start failing with an
  expired-token error.
