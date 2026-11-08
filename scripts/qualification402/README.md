# Application402: exact two-Q2 synthetic demo

The owner authorized A+D1 only for the exact A/B input,0–200s and the sealed
[plan](plan.json). Read the [result](../../docs/q2-application-acceptance-402.md)
and its separate numerical/effect/domain/release verdicts. This is not a general
benchmark framework, a new solver or permission to rerun the completed22jobs.

- `execute.py`: imports exacta99f73a source and384dependencies; reuses the existing
  Experiment/RotationDOP853 and real Tk buttons/poll/threadpool. GUI baseline and
  repeats use actual target/save/load widgets; dialog answers are test-controlled.
- `metrics.py`: read-only eleven-observable D1 calculation. It keeps scalar
  separation distinct from the relative position vector, raw R unchanged, and
  uses polar projection only in the observer. N_sens is operational sensitivity,
  not an absolute roundoff or global-error bound.
- `audit.py`: rechecks raw receipts/source/IC/checkpoints, Decimal80/120 scalar
  observations and EPL, SVD-vs-eigen polar geometry and quaternion-vs-matrix angles.
  It shares physical definitions/IC/SciPy; this is not external peer review.
- [Portable tests](../../tests/test_q2_application402.py) cover geometry, tiny/pi
  angles, exact initial spin budgets and the fixed22ID inventory without orbits.

The separately archived raw402 artifacts contain the immutable plan and executed
tool versions, guards, commands, all failed attempts and their CPU ledger.
Version1 completed one GUI case; its following continuous attempt failed while
serializing the t0 coordinate readout. The completed case was authenticated and
reused. Only the unconfirmed continuous attempt was restarted in a new directory;
there are22logical completed jobs and23scientific integration attempts.
Reference spin readout association and an observer output-index error were then
corrected offline, preserving old code/receipts and all raw states. No integrator,
force, tolerance or accepted numerical array was changed.

Execution binds local paths intentionally. Old v1/v2 manifests refer to their
exact archived source bytes; current observer revisions have separate manifests.
The closed executor is not a reusable live CLI: do not bypass its old bindings to
rerun completed cases. Restore the archived versions only to inspect provenance.
The final read-only auditor binds tools-v4. New work needs an explicit new plan.

Known limitations: missing10m scalar-distance effect; four new short strict
convergence FAIL; three historicalFAIL380; Tcl pending-after messages when this
test runner destroys/recreates Tk roots in one process; outdated A/D1 approval
text in the exact candidate. None was hidden or fixed in production here.
