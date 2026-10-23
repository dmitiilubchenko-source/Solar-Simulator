"""0.3.1 acceptance against installed packages, in a fresh isolated workspace."""
from concurrent.futures import CancelledError
from dataclasses import replace
import json
import os
from pathlib import Path
import sys
from threading import Event, get_ident
import tkinter as tk
from unittest.mock import patch


def run():
    if not sys.flags.isolated or not Path(os.environ['LOCALAPPDATA']).resolve().is_relative_to(Path.cwd()):
        raise RuntimeError('Use isolated Python and a workspace-local LOCALAPPDATA')
    from solar_simulator.app import Laboratory
    from solar_simulator.branch_io import open_experiment, save_experiment
    from solar_simulator.experiment import Settings, advance, create_experiment
    from solar_simulator.recovery import list_recoveries
    from solar_simulator.sandbox import branch_experiment
    from solar_simulator.simulation import Body
    from solar_simulator.storage import to_document
    from solar_simulator.trajectory import record_trajectory
    from solar_simulator.trajectory_loader import TrajectoryLoader, prepare_trajectory
    from solar_simulator.vector3 import Vector3

    workspace = Path('patch031 workflows')
    workspace.mkdir(exist_ok=False)
    seed = create_experiment([Body('probe', 1., Vector3(1, 2, 3), Vector3(2, 3, 4))], Settings(1.))
    parent = advance(seed, 10)
    branch = branch_experiment(parent, replacements=(('probe', replace(parent.bodies[0], mass=2.)),))
    current = advance(branch.child, 3)
    incoming = workspace/'incoming.json'
    save_experiment(seed, incoming)
    root = tk.Tk()
    root.withdraw()
    app = Laboratory(root, current, parent_snapshot=branch.parent_snapshot)
    actions = (app._new, app._reset, app._load, app._open_lunar_rotation,
               app._open_solar_sandbox, lambda:app._restore_recovery(incoming))
    transitions = failures = 0
    loader = None
    release = Event()
    try:
        for action in actions:
            app._set_experiment(current, parent_snapshot=branch.parent_snapshot)
            before = len(list_recoveries())
            with patch('solar_simulator.app.filedialog.askopenfilename', return_value=str(incoming)):
                action()
            saved, snapshot = open_experiment(app.last_recovery_path)
            assert to_document(saved) == to_document(current) and snapshot == branch.parent_snapshot
            assert len(list_recoveries()) == before+1
            transitions += 1
        app._set_experiment(current, parent_snapshot=branch.parent_snapshot)
        for action in actions:
            with patch('solar_simulator.app.filedialog.askopenfilename', return_value=str(incoming)), \
                 patch('solar_simulator.recovery.save_recovery', side_effect=OSError('controlled patch031 disk failure')):
                try:action()
                except OSError as error:assert str(error) == 'controlled patch031 disk failure'
                else:raise AssertionError('Replacement must fail when preservation fails')
            assert app.experiment is current and app.parent_snapshot == branch.parent_snapshot
            failures += 1

        directory = workspace/'free track'
        record_trajectory(seed, directory, 10., packet_steps=1)
        original = {p.name:p.read_bytes() for p in directory.iterdir()}
        for cancel in (False, True):
            entered = Event()
            release = Event()
            threads = []
            def held(*args):
                threads.append(get_ident())
                entered.set()
                if not release.wait(10):raise TimeoutError('Reader acceptance was not released')
                return prepare_trajectory(*args)
            with patch('solar_simulator.trajectory_loader.prepare_trajectory', side_effect=held):
                loader = TrajectoryLoader(tk.Toplevel(root), directory)
                assert entered.wait(5)
                heartbeat = []
                root.after(0, lambda:heartbeat.append(get_ident()))
                root.update()
                assert heartbeat == [get_ident()] and threads[0] != get_ident()
                assert not loader.future.done()
                if cancel:loader.close()
                release.set()
                if cancel:
                    try:loader.future.result(timeout=10)
                    except CancelledError:pass
                    else:raise AssertionError('Cancelled reader must not open a viewer')
                    assert loader.viewer is None
                else:
                    loader.future.result(timeout=10)
                    loader._poll()
                    viewer = loader.viewer
                    assert viewer is not None and len(viewer.frames) == 11
                    artists = (id(viewer._plot_artists.paths), id(viewer._plot_artists.markers))
                    with patch('solar_simulator.experiment.advance', side_effect=AssertionError('Playback invoked solver')):
                        for index in (1, 5, 10):
                            viewer.player.seek(index)
                            viewer._draw()
                            assert artists == (id(viewer._plot_artists.paths), id(viewer._plot_artists.markers))
                            assert tuple(viewer._plot_artists.paths.get_segments()[0][-1]) == (1+2*index, 2+3*index)
                    viewer.close()
            assert original == {p.name:p.read_bytes() for p in directory.iterdir()}
            assert app.experiment is current
    finally:
        release.set()
        if loader is not None and not loader.closed:loader.close()
        app.close()
    return dict(isolated=sys.flags.isolated, preserved_transitions=transitions,
                rejected_write_failures=failures, reader_off_Tk_thread=True,
                Tk_heartbeat=True, cancellation_preserves_recording=True,
                analytic_free_motion_frames=True, playback_no_solver=True,
                persistent_artists=True, physical_accuracy_claim=False)


if __name__ == '__main__':
    print(json.dumps(run()))
