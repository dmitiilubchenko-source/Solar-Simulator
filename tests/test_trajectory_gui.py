"""Real Tk recording/playback and cooperative close, with isolated user data."""
from pathlib import Path

import pytest


def make_branch(backend='python'):
    from dataclasses import replace
    from solar_simulator.experiment import advance,preset
    from solar_simulator.sandbox import branch_experiment
    seed=preset('sun-earth',backend=backend)
    seed=replace(seed,settings=replace(seed.settings,integrator='dop853'))
    parent=advance(seed,2);body=replace(parent.bodies[0],mass=parent.bodies[0].mass*1.1)
    return branch_experiment(parent,replacements=((body.name,body),))


def _check_record_and_view(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.trajectory import Trajectory
    from solar_simulator.trajectory_view import TrajectoryViewer
    from solar_simulator.storage import to_document
    branch=make_branch();root=tk.Tk();root.withdraw()
    app=Laboratory(root,branch.child,parent_snapshot=branch.parent_snapshot)
    viewer=None
    try:
        before=to_document(app.experiment)
        app.target.set(str(app.experiment.time+app.experiment.settings.dt*5.25));app.batch.set('2')
        with patch('solar_simulator.app.filedialog.askdirectory',return_value=str(tmp_path)):
            app._record_trajectory()
        app.future.result(timeout=15);app._poll()
        assert app.future is None and app._trajectory_stop is None
        assert to_document(app.experiment)==before and app.parent_snapshot==branch.parent_snapshot
        assert app.trajectory_status=='complete' and str(app.last_trajectory_path) in app.status.get()
        track=Trajectory(app.last_trajectory_path)
        original={p.name:p.read_bytes() for p in app.last_trajectory_path.iterdir()}
        def forbidden(*args,**kwargs):raise AssertionError('Viewer called a solver')
        with patch('solar_simulator.trajectory.advance_towards',side_effect=forbidden), \
             patch('solar_simulator.experiment.advance',side_effect=forbidden):
            viewer=TrajectoryViewer(tk.Toplevel(root),track)
            viewer.window.withdraw()
            viewer.rate.set('1');viewer._play();viewer._last-=2.;viewer._tick()
            assert viewer.player.index==2
            viewer.slider.set(0)
            assert viewer.player.index==0 and not viewer.player.running
            viewer.rate.set('25');viewer._play();viewer._last-=1.;viewer._tick()
            assert viewer.player.index==len(track.times)-1 and not viewer.player.running
            assert viewer.player.state[1]==branch.parent_snapshot
            from solar_simulator.branch_io import open_experiment
            with patch('solar_simulator.trajectory_view.filedialog.asksaveasfilename',return_value=str(tmp_path/'export.json')):
                viewer._export_frame()
            saved,parent=open_experiment(tmp_path/'export.json')
            assert to_document(saved)==to_document(viewer.player.state[0]) and parent==branch.parent_snapshot
            with patch('solar_simulator.trajectory_view.filedialog.asksaveasfilename',return_value=str(app.last_trajectory_path/'manifest.json')), \
                 patch('solar_simulator.trajectory_view.messagebox.showerror') as error:
                viewer._export_frame()
            assert error.call_count==1
        assert original=={p.name:p.read_bytes() for p in app.last_trajectory_path.iterdir()}
        assert to_document(app.experiment)==before
    finally:
        if viewer is not None:viewer.close()
        app.close()


def _check_close_waits_for_recorded_packet(tmp_path):
    from threading import Event
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator import trajectory
    from solar_simulator.storage import to_document
    branch=make_branch('rust');root=tk.Tk();root.withdraw()
    app=Laboratory(root,branch.child,parent_snapshot=branch.parent_snapshot)
    entered=Event();release=Event();compute=trajectory.advance_towards;completed=[]
    def held(*args):
        entered.set();assert release.wait(10)
        result=compute(*args);completed.append(result);return result
    try:
        app.target.set(str(app.experiment.time+app.experiment.settings.dt*10));app.batch.set('2')
        with patch('solar_simulator.app.filedialog.askdirectory',return_value=str(tmp_path)), \
             patch('solar_simulator.trajectory.advance_towards',side_effect=held):
            app._record_trajectory();assert entered.wait(10)
            app._request_close()
            assert not app.closed and app.future is not None
            release.set();app.future.result(timeout=15);app._poll()
        assert app.closed and len(completed)==1
        track=trajectory.Trajectory(app.last_trajectory_path)
        assert track.metadata['status']=='stopped' and len(track.times)==2
        state,parent=track.frame(-1)
        assert to_document(state)==to_document(completed[0]) and parent==branch.parent_snapshot
    finally:
        release.set()
        if not app.closed:
            if app.future is not None:app.future.result(timeout=15);app._poll()
            if not app.closed:app.close()


def _check_invalid_folder_does_not_create_empty_viewer(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    root=tk.Tk();root.withdraw();app=Laboratory(root)
    try:
        with patch('solar_simulator.app.filedialog.askdirectory',return_value=str(tmp_path)):
            try:app._open_trajectory()
            except OSError:pass
            else:raise AssertionError('Invalid recording should fail')
        assert not any(isinstance(w,tk.Toplevel) for w in root.winfo_children())
    finally:app.close()


@pytest.mark.parametrize('journey',['_check_record_and_view','_check_close_waits_for_recorded_packet',
                                    '_check_invalid_folder_does_not_create_empty_viewer'])
def test_real_trajectory_journey(tmp_path,journey):
    from test_app_workflows import run_gui_check
    run_gui_check(journey,tmp_path,source=__file__)
