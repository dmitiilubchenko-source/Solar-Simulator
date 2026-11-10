"""Real Tk ownership, scheduled continuation and hostile controls for the oracle."""
from pathlib import Path
import pytest


def _check_poll_contract(tmp_path):
    import time
    import tkinter as tk
    from concurrent.futures import Future
    import runpy
    helpers=runpy.run_path(str(Path(__file__).with_name('test_app_workflows.py')))
    _assert_one_poll=helpers['_assert_one_poll'];_assert_worker_error=helpers['_assert_worker_error']
    from solar_simulator.app import Laboratory
    host=tk.Tk();host.withdraw();root=tk.Toplevel(host);root.withdraw()
    errors=[];host.report_callback_exception=lambda *a:errors.append(a)
    def _poll():pass  # A foreign owner may use the same callback name.
    foreign=host.after(10000,_poll);app=Laboratory(root)
    try:
        before=_assert_one_poll(app);app._poll();after=_assert_one_poll(app)
        assert before!=after and before not in host.tk.call('after','info')
        deadline=time.perf_counter()+1
        while app._poll_after_id==after and time.perf_counter()<deadline:
            host.update();time.sleep(.005)
        assert _assert_one_poll(app)!=after  # Scheduled callback really ran.
        duplicate=root.after(10000,app._poll)
        with pytest.raises(AssertionError,match='exactly one'): _assert_one_poll(app)
        root.after_cancel(duplicate)
        app._cancel_poll()
        with pytest.raises(AssertionError,match='exactly one'): _assert_one_poll(app)
        app._poll();_assert_one_poll(app)
        completed=app.experiment;failure=Future();failure.set_exception(ValueError('lost worker error'))
        app.future=failure;app.running=True
        with pytest.raises(AssertionError): _assert_worker_error(app,completed,[],1)
        # The untouched worker-error scenario remains in the original test.
        app.future=None;app.running=False
        owned=set(root._tclCommands or ())
        app.close();host.update()
        pending=host.tk.call('after','info')
        assert foreign in pending
        assert not [i for i in pending if str(host.tk.call('after','info',i)[0]) in owned]
        assert not errors
    finally:
        if not app.closed:app.close()
        host.after_cancel(foreign);host.destroy()


def test_manual_scheduled_close_and_negative_poll_controls(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_poll_contract',tmp_path,Path(__file__).resolve())
