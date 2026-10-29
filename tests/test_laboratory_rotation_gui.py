"""Existing Laboratory lifecycle, read-only snapshots and projected principal axes."""
from pathlib import Path


def _settle(loader):
    loader.future.result(timeout=10);loader._poll()
    assert hasattr(loader,'payload')


def _check_demo_journey(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.application_profiles import two_q2_demo
    from solar_simulator.storage import to_document,load
    root=tk.Tk();root.withdraw();app=Laboratory(root);views=[]
    try:
        # Point scenario still has a read-only report and no rotation axes.
        plain=to_document(app.experiment);viewer=app._show_inspection();views.append(viewer);_settle(viewer)
        assert viewer.payload['rotations']==[] and to_document(app.experiment)==plain
        app._open_two_q2();initial=to_document(app.experiment)
        assert initial==to_document(two_q2_demo())
        assert len(app._principal_axes.get_segments())==6
        assert 'без Q2–Q2' in app.model_info.get() and 'Учебные' in app.model_info.get()
        # Viewing does not apply pending controls or normalize stored q/S.
        app.dt.set('999');app.integrator.set('verlet');app.rtol.set('1e-3')
        view=app._show_inspection();views.append(view);_settle(view)
        assert view.payload['numerical_reliability']['execution']['integrator']=='RotationDOP853 (SciPy)'
        assert view.payload['numerical_reliability']['time_and_packets']['configured_dt_seconds']==50
        assert all(field.cget('state')=='disabled' for field in view.texts)
        assert to_document(app.experiment)==initial and app.dt.get()=='999'
        app._sync_settings(app.experiment.settings)
        for plane in ('XY','XZ','YZ'):
            app.plane.set(plane);app.reference.set('Тело: B');app._draw()
            assert len(app._principal_axes.get_segments())==6 and to_document(app.experiment)==initial
        app._start();app._poll();pending=app.future
        assert pending is not None
        app._pause();pending.result(timeout=10);app._poll()
        assert not app.running and app.future is None and app.experiment.time==50
        for _ in range(2):
            app._submit(1);app.future.result(timeout=10);app._poll()
        assert app.experiment.time==150 and app.experiment.settings==two_q2_demo().settings
        # Existing stop/recovery writes only when explicitly requested.
        app._stop_and_save();saved=to_document(app.experiment)
        assert to_document(load(app.last_recovery_path))==saved
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=''):app._save()
        with patch('solar_simulator.app.filedialog.askopenfilename',return_value=''):app._load()
        assert to_document(app.experiment)==saved
        path=tmp_path/'two figures.json'
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(path)):app._save()
        assert to_document(load(path))==saved
        assert view.payload['time_seconds']==0 and view.payload['rotations'][1]['quaternion']==initial['rotations'][1]['quaternion']
        app.scenario.set('sun-earth');app._select_scenario();app._new()
        assert not app.experiment.rotations and not hasattr(app,'_principal_axes')
        app._open_lunar_rotation();one=to_document(app.experiment)
        assert len(app._principal_axes.get_segments())==3
        single=app._show_inspection();views.append(single);_settle(single)
        assert len(single.payload['rotations'])==1 and to_document(app.experiment)==one
        with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(path)):app._load()
        assert to_document(app.experiment)==saved
        app._submit(1);app.future.result(timeout=10);app._poll()
        assert app.experiment.time==200 and app.experiment.settings==two_q2_demo().settings
        assert app.experiment.initial_rotations==two_q2_demo().initial_rotations
    finally:
        for view in views:
            if view.window.winfo_exists():view.close()
        app.close()


def _check_inspection_cancel_error_and_close(tmp_path):
    import tkinter as tk
    from concurrent.futures import CancelledError
    from threading import Event
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.storage import to_document
    root=tk.Tk();root.withdraw();app=Laboratory(root)
    try:
        app._open_two_q2();before=to_document(app.experiment);started=Event();release=Event()
        children=root.winfo_children()
        with patch('solar_simulator.storage.to_document',side_effect=ValueError('controlled invalid snapshot')):
            try:app._show_inspection()
            except ValueError:pass
            else:raise AssertionError('Invalid snapshot accepted')
        assert root.winfo_children()==children,'Failed capture left an empty inspection window'
        def slow(document,stopped,progress):
            started.set();assert release.wait(5)
            if stopped():raise CancelledError()
            raise AssertionError('Cancellation lost')
        with patch('solar_simulator.inspection_view.prepare_inspection',slow):
            view=app._show_inspection();assert started.wait(5);view.close();release.set()
            try:view.future.result(timeout=5)
            except CancelledError:pass
            else:raise AssertionError('Stopped viewer returned scientific output')
            assert view.closed and not hasattr(view,'payload')
        with patch('solar_simulator.inspection_view.prepare_inspection',side_effect=ValueError('controlled read error')):
            view=app._show_inspection()
            try:view.future.result(timeout=5)
            except ValueError:pass
            with patch('solar_simulator.trajectory_loader.messagebox.showerror') as message:view._poll()
            assert message.call_count==1 and not view.window.winfo_exists()
        # Closing the laboratory while a viewer is pending releases its lifecycle.
        with patch('solar_simulator.inspection_view.prepare_inspection',slow):
            release.clear();started.clear();view=app._show_inspection();assert started.wait(5)
            assert to_document(app.experiment)==before
            app.close();release.set();assert view.closed
            try:view.future.result(timeout=5)
            except CancelledError:pass
    finally:
        if not app.closed:app.close()


def test_demo_start_pause_stop_save_restore_scenarios_and_read_only_views(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_demo_journey',tmp_path,Path(__file__).resolve())


def test_inspection_cancellation_errors_and_parent_close_leave_no_state_change(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_inspection_cancel_error_and_close',tmp_path,Path(__file__).resolve())
