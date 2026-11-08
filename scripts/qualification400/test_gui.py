"""Explicit candidate-only Tk tests; no application acceptance A/D1."""
from pathlib import Path


def _check_warning_paths(tmp_path):
    from dataclasses import replace
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.inspection import experimental_q2_warning
    from solar_simulator.storage import to_document
    root=tk.Tk();root.withdraw();app=Laboratory(root);views=[]
    try:
        assert 'FAIL380' not in app.model_info.get()
        app._open_two_q2();initial=to_document(app.experiment)
        warning=experimental_q2_warning(app.experiment.rotations)
        assert warning in app.model_info.get()
        view=app._show_inspection();views.append(view);view.future.result(timeout=10);view._poll()
        assert all(warning in field.get('1.0','end') for field in view.texts)
        assert to_document(app.experiment)==initial
        path=tmp_path/'two q2.json'
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(path)):app._save()
        raw=path.read_bytes()
        app.scenario.set('sun-earth');app._select_scenario();app._new()
        assert 'FAIL380' not in app.model_info.get()
        with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(path)):app._load()
        assert warning in app.model_info.get() and to_document(app.experiment)==initial
        assert path.read_bytes()==raw
        with patch('solar_simulator.app.filedialog.askopenfilename',return_value=''):app._load()
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=''):app._save()
        assert to_document(app.experiment)==initial and path.read_bytes()==raw
        # Start ignores the target field; target mode uses it. No _poll/solver call.
        app.target.set('200');app._start()
        assert app.running and app.target_time is None
        app._pause();app._start_target();assert app.target_time==200
        app._pause();assert to_document(app.experiment)==initial
        single=replace(app.experiment,rotations=app.experiment.rotations[:1],initial_rotations=app.experiment.initial_rotations[:1])
        app._set_experiment(single)
        assert 'FAIL380' not in app.model_info.get()
    finally:
        for view in views:
            if view.window.winfo_exists():view.close()
        app.close()


def _check_bad_load(tmp_path):
    import json,tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.storage import to_document
    root=tk.Tk();root.withdraw();app=Laboratory(root)
    try:
        app._open_two_q2();initial=to_document(app.experiment)
        bad=json.loads(json.dumps(initial));bad['settings']['rtol']=True
        path=tmp_path/'invalid.json';path.write_text(json.dumps(bad),encoding='utf8');raw=path.read_bytes()
        with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(path)):
            try:app._load()
            except ValueError:pass
            else:raise AssertionError('Bad settings accepted')
        assert to_document(app.experiment)==initial and path.read_bytes()==raw
    finally:app.close()


def test_demo_load_model_report_start_and_cancel(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_warning_paths',tmp_path,Path(__file__).resolve())


def test_bad_loaded_data_leave_current_experiment_and_file_unchanged(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_bad_load',tmp_path,Path(__file__).resolve())
