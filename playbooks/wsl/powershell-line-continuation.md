# PowerShell line continuation

Never use `^` or backtick (`` ` ``) line continuation in PowerShell — a `--flag`
at the start of a continued line is parsed as a decrement operator and the
command misbehaves.

Use **array splatting** instead:

```powershell
$args = @('--flag', 'value', '--other', 'x')
& my-exe @args
```

This keeps long invocations readable without fragile continuations.
