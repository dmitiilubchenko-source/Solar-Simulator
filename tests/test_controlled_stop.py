"""Cancellation commits only complete packets and preserves immediate parents."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from solar_simulator.experiment import advance, preset
from solar_simulator.branch_io import open_experiment, save_experiment
from solar_simulator.sandbox import branch_experiment
from solar_simulator.storage import to_document


def branch():
    parent = advance(preset('sun-earth'), 2)
    changed = replace(parent.bodies[0], mass=parent.bodies[0].mass*1.1)
    return branch_experiment(parent, replacements=((changed.name, changed),))


def test_recovery_is_unique_and_preserves_full_branch(tmp_path):
    from solar_simulator.recovery import save_recovery
    original = branch()
    paths = [save_recovery(original.child, parent_snapshot=original.parent_snapshot,
                           directory=tmp_path, reason='interrupted') for _ in range(2)]
    assert paths[0] != paths[1] and all(path.is_file() for path in paths)
    for path in paths:
        child, parent = open_experiment(path)
        assert to_document(child) == to_document(original.child) and parent == original.parent_snapshot


def test_failed_recovery_does_not_damage_previous_copy(tmp_path, monkeypatch):
    from solar_simulator.recovery import save_recovery
    initial = preset('sun-earth')
    previous = save_recovery(initial, directory=tmp_path)
    raw = previous.read_bytes()
    def fail(*args): raise OSError('controlled disk failure')
    monkeypatch.setattr('solar_simulator.storage.os.replace', fail)
    with pytest.raises(OSError): save_recovery(initial, directory=tmp_path)
    assert previous.read_bytes() == raw
    assert len(list(tmp_path.glob('*/checkpoint.json'))) == 1


@pytest.mark.parametrize('failure', ['interrupt', 'worker'])
@pytest.mark.parametrize('completed_packets', [0, 1])
def test_cli_interrupt_or_failure_preserves_last_packet_and_parent(tmp_path, monkeypatch, capsys, failure, completed_packets):
    from solar_simulator import commands
    original = branch()
    source, output = tmp_path/'input.json', tmp_path/'output.json'
    save_experiment(original.child, source, parent_snapshot=original.parent_snapshot)
    source_raw = source.read_bytes(); output.write_bytes(b'previous completed output')
    compute = commands.advance_towards
    committed = []
    def controlled(state, target, steps):
        if len(committed) >= completed_packets:
            if failure == 'interrupt': raise KeyboardInterrupt
            raise RuntimeError('controlled worker failure')
        result = compute(state, target, steps)
        committed.append(to_document(result))
        return result
    monkeypatch.setattr(commands, 'advance_towards', controlled)
    args = ['run-until', str(source), str(output), '--time', str(original.child.settings.dt*5), '--batch', '2']
    if failure == 'interrupt':
        try: result = commands.main(args)
        except KeyboardInterrupt: pytest.fail('run-until did not save the interrupted state')
        assert result == 130
    else:
        with pytest.raises(SystemExit) as exit: commands.main(args)
        assert exit.value.code == 2
    recovered = list(tmp_path.glob('solar-*/checkpoint.json'))
    assert len(recovered) == 1
    child, parent = open_experiment(recovered[0])
    expected = committed[-1] if committed else to_document(original.child)
    assert to_document(child) == expected and parent == original.parent_snapshot
    assert source.read_bytes() == source_raw and output.read_bytes() == b'previous completed output'
    diagnostic = json.loads(capsys.readouterr().err.splitlines()[0])
    assert Path(diagnostic['recovery_path']) == recovered[0]
    assert diagnostic['last_committed_time_seconds'] == child.time


def test_invalid_cli_request_does_not_create_recovery(tmp_path):
    from solar_simulator.commands import main
    source = tmp_path/'input.json'; save_experiment(preset('sun-earth'), source)
    with pytest.raises(SystemExit):
        main(['run-until', str(source), str(tmp_path/'output.json'), '--time', '-1'])
    assert not list(tmp_path.glob('solar-*'))


def _check_gui_pending_close(tmp_path):
    from concurrent.futures import Future
    import os
    import tkinter as tk
    from solar_simulator.app import Laboratory
    os.environ['LOCALAPPDATA'] = str(tmp_path/'local data')
    original = branch()
    root = tk.Tk(); root.withdraw()
    app = Laboratory(root, original.child, parent_snapshot=original.parent_snapshot)
    pending = Future()
    try:
        assert app.parent_snapshot == original.parent_snapshot
        app.future = pending; app.running = True
        app.close()
        app._request_close(); app._stop_and_save()
        assert not app.closed and app.future is pending and not app.running
        assert not list(tmp_path.rglob('checkpoint.json'))
        completed = advance(original.child, 2)
        pending.set_result(completed); app._poll()
        assert app.closed and app.future is None
        recovered = list(tmp_path.rglob('checkpoint.json'))
        assert len(recovered) == 1
        child, parent = open_experiment(recovered[0])
        assert to_document(child) == to_document(completed) and parent == original.parent_snapshot
    finally:
        if not app.closed:
            app.future = None; app.close()


def _check_gui_failure_and_retry(tmp_path):
    from concurrent.futures import Future
    import os
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    os.environ['LOCALAPPDATA'] = str(tmp_path/'local data')
    root = tk.Tk(); root.withdraw(); app = Laboratory(root)
    original = to_document(app.experiment); errors = []
    try:
        pending = Future(); app.future = pending; app.running = True
        app._request_close()
        pending.set_exception(RuntimeError('controlled worker failure'))
        with patch('solar_simulator.app.messagebox.showerror', side_effect=lambda *a,**k: errors.append(a)), \
             patch('solar_simulator.recovery.save_recovery', side_effect=OSError('controlled disk failure')):
            app._poll()
        assert not app.closed and app.future is None and not app.running
        assert to_document(app.experiment) == original and len(errors) == 2
        assert not list(tmp_path.rglob('checkpoint.json'))
        app._request_close()
        assert app.closed
        path = next(tmp_path.rglob('checkpoint.json'))
        assert to_document(open_experiment(path)[0]) == original
    finally:
        if not app.closed: app.close()


def _check_gui_stop_keeps_window_and_does_not_submit_next_packet(tmp_path):
    from concurrent.futures import Future
    import os
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    os.environ['LOCALAPPDATA'] = str(tmp_path/'local data')
    root = tk.Tk(); root.withdraw(); app = Laboratory(root)
    try:
        initial = app.experiment; pending = Future(); app.future = pending; app.running = True
        app._stop_and_save()
        assert app.future is pending and not app.running and not app.closed
        completed = advance(initial, 2); pending.set_result(completed)
        with patch.object(app.pool, 'submit', side_effect=AssertionError('No next packet')):
            app._poll()
        assert not app.closed and app.future is None
        assert to_document(open_experiment(app.last_recovery_path)[0]) == to_document(completed)
        assert app.experiment.settings == initial.settings and str(app.last_recovery_path) in app.status.get()
    finally: app.close()


def _check_gui_worker_failure_without_close_saves_previous_state(tmp_path):
    from concurrent.futures import Future
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    root = tk.Tk(); root.withdraw(); app = Laboratory(root)
    original = to_document(app.experiment)
    try:
        failed = Future(); failed.set_exception(RuntimeError('controlled failure'))
        app.future = failed; app.running = True
        def check_saved_before_notification(*args, **kwargs):
            assert app.last_recovery_path is not None and app.last_recovery_path.is_file()
            assert to_document(open_experiment(app.last_recovery_path)[0]) == original
        with patch('solar_simulator.app.messagebox.showerror',side_effect=check_saved_before_notification):
            app._poll()
        assert not app.closed and not app.running and app.future is None
        assert to_document(open_experiment(app.last_recovery_path)[0]) == original
    finally: app.close()


@pytest.mark.parametrize('journey', ['_check_gui_pending_close', '_check_gui_failure_and_retry',
                                   '_check_gui_stop_keeps_window_and_does_not_submit_next_packet',
                                   '_check_gui_worker_failure_without_close_saves_previous_state'])
def test_real_gui_cooperative_stop(tmp_path, journey):
    from test_app_workflows import run_gui_check
    run_gui_check(journey, tmp_path, source=__file__)


def test_cli_does_not_report_saved_when_recovery_write_fails(tmp_path, monkeypatch):
    from solar_simulator import commands
    source, output = tmp_path/'input.json', tmp_path/'output.json'
    save_experiment(preset('sun-earth'), source); output.write_bytes(b'keep existing output')
    def interrupt(*args): raise KeyboardInterrupt
    def disk_failure(*args, **kwargs): raise OSError('disk failure')
    monkeypatch.setattr(commands, 'advance_towards', interrupt)
    monkeypatch.setattr('solar_simulator.recovery.save_recovery', disk_failure)
    with pytest.raises(SystemExit) as exit:
        commands.main(['run-until', str(source), str(output), '--time', '1'])
    assert exit.value.code == 2 and output.read_bytes() == b'keep existing output'
