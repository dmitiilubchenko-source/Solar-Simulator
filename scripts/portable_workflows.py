"""Isolated acceptance of the shipped editor/recording/restart/view/replay chain.

Run by check_portable with the extracted interpreter, never the host package.
The create and restore phases must run in different processes and one workspace.
"""
import json
from math import isclose, sqrt
from pathlib import Path
import subprocess
import sys
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch


WORKSPACE = Path('acceptance workflows')


def vector(actual, expected):
    assert all(isclose(a, b, rel_tol=0., abs_tol=1e-10) for a, b in zip(actual, expected, strict=True)), (actual, expected)


def select(root, widget, index):
    widget.current(index)
    widget.event_generate('<<ComboboxSelected>>')
    root.update()


def create():
    from threading import Event
    from solar_simulator import trajectory
    from solar_simulator.app import Laboratory
    from solar_simulator.branch_io import open_experiment
    from solar_simulator.experiment import Settings, create_experiment
    from solar_simulator.simulation import Body
    from solar_simulator.storage import to_document
    from solar_simulator.vector3 import Vector3
    WORKSPACE.mkdir(exist_ok=False)
    result = {}
    for backend, integrator in (('python', 'dop853'), ('rust', 'verlet')):
        directory = WORKSPACE/backend
        directory.mkdir()
        seed = create_experiment([Body('free', 1., Vector3(3., 4., 5.), Vector3(2., -1., .5),
                                       spin=Vector3(1., 2., 3.))],
                                 Settings(10., backend=backend, integrator=integrator))
        trajectory.record_trajectory(seed, directory/'parent', 60., packet_steps=2)
        parent = trajectory.Trajectory(directory/'parent').frame(1)[0]
        root = tk.Tk()
        root.withdraw()
        app = Laboratory(root, parent)
        entered, release = Event(), Event()
        try:
            app._edit()
            dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
            fields = dialog.body_fields
            for widget, index in ((fields.mass_unit, 1), (fields.length_unit, 1),
                                  (fields.speed_unit, 1), (fields.reference, 1)):
                select(root, widget, index)
            for key, value in dict(mass='2', x='0', y='0', z='0', vx='.003', vy='.002', vz='-.001').items():
                fields.variables[key].set(value)
            button = next(w for w in dialog.winfo_children() if isinstance(w, ttk.Button))
            branch_file = directory/'edited.json'
            with patch('solar_simulator.app.filedialog.asksaveasfilename', return_value=str(branch_file)):
                button.invoke()
            child, snapshot = open_experiment(branch_file)
            assert to_document(child) == to_document(app.experiment) and snapshot == app.parent_snapshot
            assert child.bodies[0].mass == 1.19444e25
            assert tuple(getattr(child.bodies[0].spin, a) for a in 'xyz') == (1., 2., 3.)
            vector(tuple(getattr(child.bodies[0].position, a) for a in 'xyz'), (43., -16., 15.))
            vector(tuple(getattr(child.bodies[0].velocity, a) for a in 'xyz'), (5., 1., -.5))
            original = to_document(app.experiment)
            app.target.set('40')
            app.batch.set('2')
            with patch('solar_simulator.app.filedialog.askdirectory', return_value=str(directory.resolve())):
                app._record_trajectory()
            app.future.result(timeout=60)
            app._poll()
            complete = app.last_trajectory_path
            assert app.trajectory_status == 'complete' and to_document(app.experiment) == original
            # Hold one unchanged packet to make the cooperative-close boundary deterministic.
            compute = trajectory.advance_towards
            def held(*args):
                entered.set()
                if not release.wait(20):
                    raise TimeoutError('Acceptance did not release the original packet')
                return compute(*args)
            app.target.set('100000')
            with patch('solar_simulator.app.filedialog.askdirectory', return_value=str(directory.resolve())), \
                 patch('solar_simulator.trajectory.advance_towards', side_effect=held):
                app._record_trajectory()
                assert entered.wait(60)
                app._request_close()
                assert not app.closed
                release.set()
                app.future.result(timeout=60)
                app._poll()
            assert app.closed and app.last_recovery_path.is_file()
            stopped = trajectory.Trajectory(app.last_trajectory_path)
            assert stopped.metadata['status'] == 'stopped' and stopped.times == (0., 20.)
            recovered, recovered_parent = open_experiment(app.last_recovery_path)
            assert to_document(recovered) == original and recovered_parent == snapshot
            result[backend] = dict(complete=str(complete), stopped=str(app.last_trajectory_path),
                                   recovery=str(app.last_recovery_path))
        finally:
            release.set()
            if not app.closed:
                app.close()
    (WORKSPACE/'stage.json').write_text(json.dumps(result), encoding='utf-8')
    return dict(isolated=sys.flags.isolated, edited_recorded_closed=list(result))


def restore():
    import hashlib
    from solar_simulator.app import Laboratory
    from solar_simulator.branch_io import open_experiment
    from solar_simulator.comparison import Comparison
    from solar_simulator.comparison_view import ComparisonViewer
    from solar_simulator.storage import to_document
    from solar_simulator.trajectory import Trajectory
    from solar_simulator.trajectory_view import TrajectoryViewer
    paths = json.loads((WORKSPACE/'stage.json').read_bytes())
    results = {}
    for backend, paths_for_backend in paths.items():
        directory = WORKSPACE/backend
        child = Trajectory(paths_for_backend['complete'])
        assert child.times == (0., 20., 40.)
        for index, time in enumerate(child.times):
            state, _ = child.frame(index)
            vector(tuple(getattr(state.bodies[0].position, a) for a in 'xyz'),
                   (43+5*time, -16+time, 15-.5*time))
        # Full source bytes must survive viewing, auditing, export and replay.
        original = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.rglob('*') if p.is_file()}
        recovered, snapshot = open_experiment(paths_for_backend['recovery'])
        root = tk.Tk()
        root.withdraw()
        app = Laboratory(root, recovered, parent_snapshot=snapshot)
        viewers = []
        try:
            app._submit(2)
            app.future.result(timeout=30)
            app._poll()
            assert to_document(app.experiment) == to_document(child.frame(1)[0]) and app.parent_snapshot == snapshot
            comparison = Comparison(Trajectory(directory/'parent'), child, event_side='after')
            assert comparison.anchor_time == 20. and comparison.times == (0., 20., 40.)
            for index, time in enumerate(comparison.times):
                row = comparison.sample(index)['bodies']['free']
                vector(row['delta_position_m'], (3*time, 2*time, -time))
                vector(row['delta_velocity_m_per_s'], (3., 2., -1.))
                assert isclose(row['distance_m'], time*sqrt(14.), rel_tol=0., abs_tol=1e-10)
            def forbidden(*args, **kwargs):
                raise AssertionError('Read-only viewer invoked a solver')
            with patch('solar_simulator.trajectory.advance_towards', side_effect=forbidden), \
                 patch('solar_simulator.experiment.advance', side_effect=forbidden):
                viewer = TrajectoryViewer(tk.Toplevel(root), child)
                viewers.append(viewer)
                viewer.window.withdraw()
                viewer.player.play()
                viewer.player.tick(2., 1.)
                viewer._draw()
                assert viewer.player.index == 2 and not viewer.player.running
                viewer.slider.set(0)
                viewer.rate.set('50')
                viewer._play()
                viewer._last -= 1.
                viewer._tick()
                assert viewer.player.index == 2
                with patch('solar_simulator.trajectory_view.filedialog.asksaveasfilename',
                           return_value=str(directory/'export.json')):
                    viewer._export_frame()
                exported, exported_parent = open_experiment(directory/'export.json')
                assert to_document(exported) == to_document(child.frame(2)[0]) and exported_parent == snapshot
                overlay = ComparisonViewer(tk.Toplevel(root), comparison)
                viewers.append(overlay)
                overlay.window.withdraw()
                overlay.slider.set(2)
                overlay.canvas.draw()
                assert overlay.index == 2
                with patch('solar_simulator.comparison_view.filedialog.asksaveasfilename',
                           return_value=str(directory/'comparison.json')):
                    overlay._export()
                assert len(json.loads((directory/'comparison.json').read_bytes())['samples']) == 3
            for command, arguments in (
                ('check-recipe', [str(child.directory)]),
                ('replay-trajectory', [str(child.directory), str(directory/'replay')]),
                ('replay-trajectory', [paths_for_backend['stopped'], str(directory/'replay-stopped')]),
            ):
                process = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-I', '-m', 'solar_simulator',
                                          command, *arguments], capture_output=True, text=True,
                                         encoding='utf-8', timeout=90)
                assert process.returncode == 0, process.stdout+process.stderr
                report = json.loads(process.stdout)
                assert report.get('compatible', report.get('reproduced_prefix')) is True
                assert report['physical_accuracy_claim'] is False
            assert all(hashlib.sha256(p.read_bytes()).hexdigest() == sha for p, sha in original.items())
            results[backend] = dict(analytic_position_abs_m=1e-10, relative_tolerance=0.,
                                   complete_samples=3, stopped_samples=2, restart_exact=True,
                                   playback_no_solver=True, comparison_analytic=True, CLI_replay_exact=True)
        finally:
            for viewer in viewers:
                viewer.close()
            app.close()
    return dict(isolated=sys.flags.isolated, results=results, physical_accuracy_claim=False)


if __name__ == '__main__':
    phase = sys.argv[1]
    result = {'create': create, 'restore': restore}[phase]()
    print(json.dumps(result))
