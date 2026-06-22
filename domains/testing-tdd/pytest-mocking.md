# pytest mocking gotchas

## Patched `os.path.exists` breaks `os.makedirs`

`patch('os.path.exists', return_value=True)` makes `os.makedirs` see all
intermediate dirs as existing, then fail on the actual `os.mkdir`. Always patch
both together:

```python
@patch('os.makedirs')
@patch('os.path.exists', return_value=True)
def test_x(mock_exists, mock_makedirs): ...
```

## MagicMock identity in assertions

`assert_called_once_with(MagicMock(), ...)` always fails on the object arg —
each `MagicMock()` call is a distinct object. Capture the mock first, or assert
specific positional args:

```python
assert call.args[0] is expected_obj          # or
assert mock.call_args[0][1] == expected_value
```

## Mock used as a context manager

`MagicMock()` used in a `with` returns `__enter__.return_value` (a fresh mock),
not itself. For code like `with urlopen(...) as resp: resp.status`:

```python
resp = MagicMock(status=200)
resp.__enter__ = MagicMock(return_value=resp)   # now resp.status is reachable inside `with`
```

## Patchable optional imports

For module names that must be patchable without the real dependency installed,
declare them `try/except ImportError: name = None` — see
`domains/python/optional-dependencies-and-platform-imports.md`.
