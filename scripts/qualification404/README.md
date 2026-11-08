# Owned GUI callback teardown404

Read [the report](../../docs/q2-gui-lifecycle-fix-404.md) and [sealed plan](plan.json).
The candidate is based on exacte9ddd35. Only app.py/control_row.py change; this
is GUI lifecycle behavior, **not** a presentation-only patch or new science.

`baseline.py` preserves the original403minimal assertion FAIL on exacte9 before
edits. `check_gui.py` runs18fixed nonorbital cases with real Tk timers, recorded
command names/afterIDs/cancellation owners, continued Tcl processing and a real
executor returning saved402frame100. Unexpected Tcl/Python/UI errors fail the
case; expected disk/worker faults are recorded separately. No orbital solver is
called. Raw results and each completed receipt are immutable.

`audit.py` rechecks the raw callbacks, right-owner cancellations, no owned pending
callbacks after destroy, exact recovery bytes, source/native identity and fresh
fingerprint. The separate [lifecycle scope guard](../q2_lifecycle_delta404.py)
proves the existing dispatch/recovery and geometry bodies remain unchanged.
[Portable controls](../../tests/test_q2_lifecycle404.py) reject changes outside
the allowed methods/import/byte scope without starting Tk or physical solvers.

Production cleanup:

- Laboratory keeps/cancels its poll ID; manual calls replace a pending timer.
  Normal polling remains40ms. A stop/close request still polls an active worker
  until its packet/recovery finishes; final destroy cancels owned callbacks.
- ControlRow cancels its own idle ID, refuses scheduling during teardown and is
  safe to destroy repeatedly. Active callbacks are not cancelled as pending.
- Embedded TkAgg has no FigureManagerTk cleanup. The canvas owns _idle_draw_id
  and _event_loop_id; get_tk_widget().after_cancel cancels them on the owner.
  The fields, types, expected callback names and widget._tclCommands membership
  are checked before mutation. Unknown/foreign contracts refuse destruction.

This uses private Matplotlib/Tkinter ownership details. The qualified environment
is Matplotlib3.11.0/Python3.14.2t. Shape/ownership checks cannot prove that every
future version retaining the same fields has identical semantics; dependency
upgrades require this GUI matrix again. No Matplotlib/global queue patch or
cancel-all is used; other windows/figures remain live.

The old scientific warning is deliberately unchanged and still says lifecycle
is unresolved. Its later correction needs a separate literal/fingerprint audit.
Historical402numerical11/11 and effects10/11/distanceFAIL,4short and3historical
convergenceFAIL are preserved. No release, main/tag/LATEST/portable changes.

The executed guards/commands/profile bytes/raw logs are archived separately.
Paths and hashes intentionally bind this PC; do not rerun completed cases or
replace old receipts. No general lifecycle framework or new solver is introduced.
