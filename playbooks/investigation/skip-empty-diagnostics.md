# Skip empty-by-design diagnostics

If you know the input data can't support a diagnostic — its denominator depends
on data the file doesn't contain (e.g. an IfcSpace-IoU comparison on a file with
0 IfcSpace entities) — do **not** implement it.

- Document it under "alternatives considered" in the report instead.
- An always-empty diagnostic is noise; a documented alternative is honesty.

Applies to any quality metric whose denominator depends on absent data.
