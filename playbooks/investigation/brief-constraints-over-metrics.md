# Brief constraints over metric improvement

When a brief explicitly forbids using source X to produce an output, do **not**
loosen the constraint to improve an internal metric (agreement %, coverage,
etc.) — even when the loosening seems narrow ("I only use X for filtering, not
for the assignment").

Instead:

1. Ship the **brief-faithful** pipeline.
2. Add a **diagnostic** that surfaces the divergence the constraint creates.
3. Explain the trade-off in the report.

"100% of disagreements explained by authoring conventions" is far easier to
defend in review than "I coupled the signals to raise the number." Case study:
reconciling IFC spatial-containment against geometry-derived containment.
