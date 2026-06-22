# EventBridge: validate the pattern before deploy

For any non-trivial `AWS::Events::Rule` `EventPattern` (especially ECS-payload
filters like `detail.group`, `detail.taskDefinitionArn`), validate offline
before pushing:

```bash
aws events test-event-pattern \
  --event-pattern '{ "detail": { "group": ["service:foo"] } }' \
  --event '{ "detail": { "group": "service:foo" }, ... }'      # → Result: true
```

Construct **one positive** event (should match → `true`) and **one negative**
(should not match → `false`). This catches filter typos (e.g. `service:foo` vs
`service:foo-bar`) in seconds, before the CI deploy cycle.

Pair with `aws cloudformation validate-template --template-body file://template.yml`
for a full pre-flight.
