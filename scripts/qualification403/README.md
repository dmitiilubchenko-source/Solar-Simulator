# Truthful Q2 text and nonorbital GUI diagnostics403

Read [the report](../../docs/q2-ui-lifecycle-403.md) and [sealed plan](plan.json).
The new candidate changes one literal warning only. It does not fix GUI teardown,
alter scientific results, or authorize application/release acceptance.

`presentation.py` checks full Git/AST/bytes, actual new environment and0/1/2/custom
read-only UI states. The strict [text guard](../q2_text_delta403.py) rejects other
AST/byte changes. [Portable negative tests](../../tests/test_q2_text403.py) need
neither an archive nor a GUI.

`lifecycle.py` runs on originala99, with all evolution paths disabled. Its worker
control returns a previously saved402state through the actual executor/poll;
no orbit is computed. The probes record after IDs, Tcl command names, Python
registration stacks, errorInfo and monotonic registration/error times. A custom
Tcl bgerror handler records the real errors instead of displaying modal dialogs;
it does not prevent the dangling command execution.

The first cancellation probe exposed a harness bug: root.after_cancel deleted
a child's Tcl command while the child's Python ownership list retained it.
The corrected diagnostic calls after_cancel on the registering widget. This is
a test-harness correction, not a production fix. Completed probes were not rerun;
the remaining independent interpreters shared one Python import to fit the same
budget. A multi-root probe without event processing was nondiagnostic and is
reported separately from the corrected event-processing control.

The retained-interpreter single-root and group-isolated probes demonstrate that
production destroy leaves pending callbacks. Standalone process exit masks it.
Cancellation is only a causal control; do not silently apply it to production or
erase the failed tests. A separate lifecycle candidate and regressions are needed.

Minimal failing contract (intentionally exits with AssertionError on currenta99):

```powershell
& '<qualified-python>' -X utf8 -B scripts/qualification403/reproduce_close.py --source '<exact-a99-worktree>'
```

The fully instrumented single_with_pump probe already executes that lifecycle;
the standalone convenience script is supplied without repeating the probe.
Historical402raw logs lack callback timestamps; do not synthesize them. Current
registration/error timestamps are relative to each probe. Destruction ordering
is captured by before/after queues; no separate destroy wall timestamp was taken.

Paths and tool/source/environment hashes intentionally bind this PC. Inspect the
archived executedv1source and immutable continuation-v2 before any recovery;
never rerun completed probes automatically. Old scientific evidence does not
become a source-bound PASS for a new fingerprint solely because its text changed.
