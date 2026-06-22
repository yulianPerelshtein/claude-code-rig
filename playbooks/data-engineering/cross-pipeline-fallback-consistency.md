# Cross-pipeline fallback consistency

When two independent code paths render the same logical entity (display,
comparison, JSON output, log line), they **must** use the IDENTICAL fallback
formula for missing/None values.

```python
# pipeline.py and cross_check.py (independent traversals)
name = entity.Name or f"<unnamed {entity.GlobalId}>"   # IDENTICAL in both
```

Otherwise the same entity gets different labels in each path → **spurious
cross-pipeline disagreements** that look like real divergences and waste
investigation time. Make the fallback a shared helper if both paths can import
one. Applies anywhere two parts of a system independently name the same thing.
