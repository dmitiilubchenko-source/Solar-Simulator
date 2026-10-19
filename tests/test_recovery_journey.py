"""Finished calculations survive output errors; recovery survives a GUI restart."""
from dataclasses import replace
import json
from pathlib import Path

import pytest

from solar_simulator.branch_io import open_experiment, save_experiment
from solar_simulator.experiment import advance, preset
from solar_simulator.sandbox import branch_experiment
from solar_simulator.storage import to_document


def make_branch(backend='python'):
    seed = preset('sun-earth', backend=backend)
    seed = replace(seed, settings=replace(seed.settings, integrator='dop853'))
    parent = advance(seed, 2)
    body = replace(parent.bodies[0], mass=parent.bodies[0].mass*1.1)
    return branch_experiment(parent, replacements=((body.name, body),))


@pytest.mark.parametrize('failure', ['missing-directory', 'denied', 'interrupt'])
def test_final_output_failure_recovers_finished_result(tmp_path, monkeypatch, capsys, failure):
    from solar_simulator import commands
    original = make_branch()
    source = tmp_path/'input.json'
    output = tmp_path/'absent'/'output.json' if failure == 'missing-directory' else tmp_path/'output.json'
    save_experiment(original.child, source, parent_snapshot=original.parent_snapshot)
    source_raw = source.read_bytes()
    if failure != 'missing-directory': output.write_bytes(b'previous output')
    expected = advance(original.child, 2)
    if failure != 'missing-directory':
        def fail(*args, **kwargs):
            if failure == 'interrupt': raise KeyboardInterrupt
            raise PermissionError('controlled final output failure')
        monkeypatch.setattr(commands, 'save_experiment', fail)
    args = ['run-until', str(source), str(output), '--time', str(expected.time), '--batch', '2']
    if failure == 'interrupt':
        try: result = commands.main(args)
        except KeyboardInterrupt: pytest.fail('Final save interruption lost the completed result')
        assert result == 130
    else:
        with pytest.raises(SystemExit) as error: commands.main(args)
        assert error.value.code == 2
    diagnostic = json.loads(capsys.readouterr().err.splitlines()[0])
    child, parent = open_experiment(diagnostic['recovery_path'])
    assert to_document(child) == to_document(expected) and parent == original.parent_snapshot
    assert diagnostic['last_committed_time_seconds'] == expected.time
    assert diagnostic['requested_target_seconds'] == expected.time and diagnostic['target_reached']
    assert source.read_bytes() == source_raw
    if failure != 'missing-directory': assert output.read_bytes() == b'previous output'
    else: assert not output.exists()


def test_final_output_recovery_falls_back_to_local_data(tmp_path, monkeypatch, capsys):
    from solar_simulator import commands, recovery
    original = make_branch()
    source = tmp_path/'input.json'; blocker = tmp_path/'not a directory'
    save_experiment(original.child, source, parent_snapshot=original.parent_snapshot)
    blocker.write_text('keep', encoding='utf-8')
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path/'local data'))
    expected = advance(original.child, 1)
    with pytest.raises(SystemExit):
        commands.main(['run-until', str(source), str(blocker/'out.json'), '--time', str(expected.time)])
    diagnostic = json.loads(capsys.readouterr().err.splitlines()[0])
    path = Path(diagnostic['recovery_path'])
    assert path.is_relative_to(recovery.recovery_directory())
    actual, parent = open_experiment(path)
    assert to_document(actual) == to_document(expected) and parent == original.parent_snapshot
    assert blocker.read_text(encoding='utf-8') == 'keep'


def test_final_output_and_both_recoveries_fail_explicitly(tmp_path, monkeypatch, capsys):
    from solar_simulator import commands
    source = tmp_path/'input.json'; output = tmp_path/'out.json'
    save_experiment(preset('sun-earth'), source); output.write_bytes(b'keep')
    def fail(*args, **kwargs): raise OSError('controlled disk failure')
    monkeypatch.setattr(commands, 'save_experiment', fail)
    monkeypatch.setattr('solar_simulator.recovery.save_recovery', fail)
    with pytest.raises(SystemExit) as error:
        commands.main(['run-until', str(source), str(output), '--time', '1'])
    assert error.value.code == 2 and output.read_bytes() == b'keep'
    diagnostic = capsys.readouterr()
    assert not diagnostic.out and 'recovery_path' not in diagnostic.err
    assert 'controlled disk failure' in diagnostic.err and 'recovery' in diagnostic.err


def test_recovery_inventory_is_local_and_keeps_damaged_files_visible(tmp_path, monkeypatch):
    from solar_simulator.recovery import list_recoveries, recovery_directory, save_recovery
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path/'local data'))
    assert list_recoveries() == () and not recovery_directory().exists()
    path = save_recovery(preset('sun-earth'))
    damaged = recovery_directory()/'solar-failed-broken'/'checkpoint.json'
    damaged.parent.mkdir(); damaged.write_bytes(b'not JSON')
    other = recovery_directory()/'unrelated'/'checkpoint.json'
    other.parent.mkdir(); other.write_bytes(b'not recovery')
    assert set(list_recoveries()) == {path, damaged}


def _create_recovery(tmp_path):
    import tkinter as tk
    from solar_simulator.app import Laboratory
    backend = (tmp_path/'backend.txt').read_text()
    original = make_branch(backend)
    save_experiment(original.child, tmp_path/'expected.json', parent_snapshot=original.parent_snapshot)
    root = tk.Tk(); root.withdraw()
    app = Laboratory(root, original.child, parent_snapshot=original.parent_snapshot)
    app._request_close()
    assert app.closed and app.last_recovery_path.is_file()
    (tmp_path/'saved-path.txt').write_text(str(app.last_recovery_path))


def _restore_recovery_and_continue(tmp_path):
    import tkinter as tk
    from tkinter import ttk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.recovery import recovery_directory
    root = tk.Tk(); root.withdraw(); app = Laboratory(root)
    original, parent = open_experiment(tmp_path/'expected.json')
    saved = Path((tmp_path/'saved-path.txt').read_text())
    damaged = recovery_directory()/'solar-failed-broken'/'checkpoint.json'
    damaged.parent.mkdir(); damaged.write_bytes(b'not JSON')
    before = to_document(app.experiment)
    dialog = app._show_recoveries()
    try:
        tree = next(w for w in dialog.winfo_children() if isinstance(w, ttk.Treeview))
        button = next(w for w in dialog.winfo_children() if isinstance(w, ttk.Button) and w.cget('text') == 'Открыть выбранную копию')
        items = tree.get_children()
        assert len(items) == 2
        def select(path):
            item = next(i for i in items if tree.item(i, 'values')[0] == path.parent.name)
            tree.selection_set(item)
        select(damaged)
        with patch('solar_simulator.app.messagebox.showerror') as error:
            button.invoke()
        assert error.call_count == 1 and dialog.winfo_exists()
        assert to_document(app.experiment) == before and app.parent_snapshot is None
        select(saved); button.invoke()
        assert not dialog.winfo_exists()
        assert to_document(app.experiment) == to_document(original) and app.parent_snapshot == parent
        continued = advance(original, 2)
        app._submit(2)
        app.future.result(timeout=10); app._poll()
        assert to_document(app.experiment) == to_document(continued) and app.parent_snapshot == parent
        app._request_close()
        restored, restored_parent = open_experiment(app.last_recovery_path)
        assert to_document(restored) == to_document(continued) and restored_parent == parent
    finally:
        if not app.closed: app.close()


@pytest.mark.parametrize('backend', ['python', 'rust'])
def test_save_close_restart_restore_continue(tmp_path, backend):
    from test_app_workflows import run_gui_check
    (tmp_path/'backend.txt').write_text(backend)
    run_gui_check('_create_recovery', tmp_path, source=__file__)
    run_gui_check('_restore_recovery_and_continue', tmp_path, source=__file__)
