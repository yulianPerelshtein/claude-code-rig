# Revealing code over defensive code

When a value has an **invariant sign** (or other invariant) given its caller,
encode the invariant explicitly rather than papering over violations.

```python
# Prefer: direction is data; a wrong-sign input surfaces as a negative output
_SIGNS = {FLAG_BELOW: -1, FLAG_ABOVE: +1}
distance = _SIGNS[flag] * (value - reference) * SCALE

# Avoid: abs() hides a future caller-side wrong-sign bug
distance = abs(value - reference) * SCALE
```

`abs()` is "defensive" but masks bugs: a later caller passing the wrong sign is
silently transformed into a plausible positive value. Letting the violation
surface (a negative number, an exception) is cheaper to debug than a silent
wrong answer.

Illustration: preferring a signed direction over an absolute value in a
geometry conversion, so a sign error surfaces instead of silently flipping.
