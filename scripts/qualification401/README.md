# Source-bound interface qualification401

This fixed recovery/comparison tool completes stage400 for exact source commits
f723a216 and a99f73a. It is not a general qualification framework or a production
solver. Read [the result and limits](../../docs/q2-interface-qualification-401.md)
before use. The presentation audit remains
[q2_presentation_delta400.py](../q2_presentation_delta400.py).

`qualify.py` authenticates the archived point runs, imports each isolated source
root, checks the actual environment, and executes only the ten missing cases.
`audit.py` independently compares saved binary64 arrays, checkpoints, diagnostics
and counters without integrating. The read-only
[recovery adapter](../q2_interface_recovery401.py) never executes archived code.

The executed immutable plan, guards, commands, versioned failed attempts, full
profiles, logs and raw documents are in the separately archived401 artifacts.
Paths in the driver intentionally bind this Windows environment; a new machine
requires a new explicit plan and provenance. Never rerun the completed jobs or
rewrite their receipts. The archive is not a replacement for exact Git source
and the qualified native/dependency environment identified in its restore recipe.

Portable synthetic regression controls live in
[test_q2_recovery401.py](../../tests/test_q2_recovery401.py). They do not need the
raw archive, native module or scientific integrations. Historical point RHS/nfev
were not recorded; three solver invocations are a source proof, not measured
historical instrumentation. The short comparisons provide no global error bound,
application acceptance or release approval.
