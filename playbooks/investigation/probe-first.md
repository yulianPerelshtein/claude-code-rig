# Probe undocumented library behaviour first

Before building a fixture or pipeline on top of **undocumented** behaviour of a
third-party library — especially SWIG / auto-generated bindings — write a
~30-line probe script and verify the behaviour directly.

- Docstrings and tutorials won't reveal it; a wrong assumption produces
  confusing fixture failures far downstream.
- The probe is cheap; the downstream debugging it prevents is not.

Concrete instance: probing how IFC spatial-structure placement actually
resolves before assuming a coordinate convention.
