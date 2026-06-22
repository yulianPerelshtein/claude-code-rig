# CloudFormation: explicit DependsOn for Rule → Logs ResourcePolicy

An `AWS::Events::Rule` does **not** implicitly depend on a sibling
`AWS::Logs::ResourcePolicy`, even when both target the same LogGroup. CFN
dependency inference only follows `!Ref` / `!GetAtt` / `!Sub`, and a rule
typically references the LogGroup ARN, not the policy.

Consequence on **first** stack creation: the rule and the policy are created in
parallel; events delivered in the seconds before the policy attaches get
`AccessDenied` and are dropped (the default event bus has no DLQ).

Fix: add an explicit dependency on the rule.

```yaml
MyRule:
  Type: AWS::Events::Rule
  DependsOn: MyLogGroupResourcePolicy
```
