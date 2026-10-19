"""User journeys run in fresh Tcl interpreters, including actual widgets."""
from pathlib import Path
import os
import subprocess
import sys


def run_gui_check(function, tmp_path, source=None):
    code = """
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('workflow_checks', sys.argv[1])
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
getattr(module, sys.argv[2])(Path(sys.argv[3]))
"""
    environment=os.environ.copy()
    environment['LOCALAPPDATA']=str(tmp_path/'appdata')
    result = subprocess.run([sys.executable, '-B', '-c', code, str(source or Path(__file__).resolve()),
                             function, str(tmp_path)], capture_output=True, text=True, timeout=40,env=environment)
    assert result.returncode == 0, result.stdout+result.stderr


def _check_scenario_selection(tmp_path):
    import tkinter as tk
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import advance
    root = tk.Tk(); root.withdraw()
    app = Laboratory(root)
    try:
        original = app.experiment
        app.scenario.set('spheres')
        app.scenario_widget.event_generate('<<ComboboxSelected>>')
        root.update()
        assert app.experiment is original, 'Selecting prepares controls; creating is explicit'
        assert app.integrator.get() == 'verlet' and app.mode.get() == 'bounce'
        app._new()
        assert len(advance(app.experiment, 2).bodies) == 2
        app._open_lunar_rotation()
        assert app.experiment.rotations and app.relative_pair.get() == 'saved'
        rotating = app.experiment
        app.scenario.set('sun-earth')
        app.scenario_widget.event_generate('<<ComboboxSelected>>')
        root.update()
        assert app.experiment is rotating
        assert app.figures.get() == 'none' and app.relative_pair.get() == 'none'
        assert app.integrator.get() == 'dop853'
        app._new()
        assert not app.experiment.rotations and len(app.experiment.bodies) == 2
        assert advance(app.experiment, 1).time > 0
    finally:
        app.close()


def test_scenario_selection_prepares_valid_controls_without_replacing_current_experiment(tmp_path):
    run_gui_check('_check_scenario_selection', tmp_path)


def test_ready_lunar_profile_preserves_previously_packaged_settings_and_provenance():
    from solar_simulator.application_profiles import lunar_rotation
    from solar_simulator.experiment import Settings, preset
    from solar_simulator.nbody_rotation import lunar_initial
    result = lunar_rotation()
    original = preset('solar-system-moon')
    assert result.settings == Settings(3600, integrator='dop853', relative_pair=('Earth', 'Moon'),
                                      position_atol=1e-7, velocity_atol=1e-13)
    def values(body):
        return (body.name, body.mass, body.radius, body.position.x, body.position.y, body.position.z,
                body.velocity.x, body.velocity.y, body.velocity.z, body.spin.x, body.spin.y, body.spin.z)
    assert [values(b) for b in result.initial] == [values(b) for b in original.initial]
    assert result.origin == original.origin
    assert result.rotations == lunar_initial(original.bodies, original.origin)


def _check_worker_recovery(tmp_path):
    from concurrent.futures import Future
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import advance
    root = tk.Tk(); root.withdraw()
    app = Laboratory(root)
    errors = []
    try:
        original = app.experiment
        app.dt.set('123')
        app.batch.set('0')
        try:
            app._start()
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid batch must reject startup')
        assert app.experiment is original, 'Rejected startup must not apply pending parameters'
        app._sync_settings(original.settings)
        pending = Future()
        app.future = pending
        app.running = True
        app._pause()
        assert not app.running and app.future is pending
        assert 'завершает пакет' in app.status.get()
        assert app.start_button.instate(['disabled'])
        pending.set_result(advance(original, 1))
        app._poll()
        assert app.future is None and app.experiment.time == original.settings.dt
        assert not app.start_button.instate(['disabled'])
        completed = app.experiment
        failure = Future(); failure.set_exception(ValueError('controlled worker failure'))
        app.future = failure; app.running = True
        with patch('solar_simulator.app.messagebox.showerror', side_effect=lambda *a, **kw: errors.append(a)):
            app._poll()
        assert app.experiment is completed and not app.running and app.future is None
        assert len(errors) == 1 and 'controlled worker failure' in errors[0][1]
        # Bad asynchronous input cannot remove the next poll callback.
        app.batch.set('bad'); app.running = True
        timers_before = len(root.tk.call('after', 'info'))
        with patch('solar_simulator.app.messagebox.showerror', side_effect=lambda *a, **kw: errors.append(a)):
            app._poll()
        assert not app.running and app.future is None and len(errors) == 2
        assert len(root.tk.call('after', 'info')) > timers_before
        app.batch.set('1')
        app._submit(1)
        app.future.result(timeout=10)
        app._poll()
        assert app.experiment.time == 2*original.settings.dt
    finally:
        app.close()


def test_invalid_start_pause_worker_failure_and_polling_recovery(tmp_path):
    run_gui_check('_check_worker_recovery', tmp_path)


def _check_lunar_checkpoint_journey(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import advance
    from solar_simulator.storage import to_document, load
    root = tk.Tk(); root.withdraw()
    app = Laboratory(root)
    errors = []
    try:
        app._open_lunar_rotation()
        initial = to_document(app.experiment)
        assert len(app.experiment.bodies) == 10
        assert app.view.get() == 'Земля и Луна' and app.reference.get() == 'Тело: Earth'
        assert {text.get_text() for text in app.orbit.get_legend().get_texts()} == {'Earth', 'Moon'}
        assert 'Полный L: орбита + вращение' in app.details.get()
        assert 'задана извне' not in app.details.get() and 'без приливов' in app.energy.get_title()
        app._submit(2); app.future.result(timeout=10); app._poll()
        checkpoint = to_document(app.experiment)
        assert checkpoint['rotations'] != initial['rotations'] and app.experiment.time == 7200
        path = tmp_path/'Лунный опыт с пробелами.json'
        with patch('solar_simulator.app.filedialog.asksaveasfilename', return_value=str(path)):
            app._save()
        assert to_document(load(path)) == checkpoint
        app._reset()
        assert to_document(app.experiment) == initial
        with patch('solar_simulator.app.filedialog.askopenfilename', return_value=str(path)):
            app._load()
        assert to_document(app.experiment) == checkpoint
        expected = to_document(advance(load(path), 1))
        app._submit(1); app.future.result(timeout=10); app._poll()
        assert to_document(app.experiment) == expected, 'Loaded GUI continuation is exact'
        # Switching the visible subset cannot change the experiment or diagnostics.
        model = app.experiment; balance = tuple(app.energies)
        app.view.set('Все тела'); app._draw()
        assert len(app.orbit.get_legend().get_texts()) == 10
        app.view.set('Земля и Луна'); app._draw()
        assert app.experiment is model and tuple(app.energies) == balance
        broken = tmp_path/'broken.json'; broken.write_text('{', encoding='utf-8')
        with patch('solar_simulator.app.filedialog.askopenfilename', return_value=str(broken)), \
             patch('solar_simulator.app.messagebox.showerror', side_effect=lambda *a, **kw: errors.append(a)):
            app._guard(app._load)
        assert len(errors) == 1 and app.experiment is model
        with patch('solar_simulator.app.filedialog.askopenfilename', return_value=''):
            app._load()
        assert app.experiment is model
        app.figure.savefig(tmp_path/'earth-moon.png')
    finally:
        app.close()


def test_lunar_view_save_load_reset_exact_continuation_and_invalid_file(tmp_path):
    run_gui_check('_check_lunar_checkpoint_journey', tmp_path)


def _check_window_layout(tmp_path):
    import tkinter as tk
    from solar_simulator.app import Laboratory
    from solar_simulator.application_profiles import lunar_rotation
    root = tk.Tk()
    app = Laboratory(root, lunar_rotation())
    try:
        root.geometry('1180x820')
        root.update()
        bottom = root.winfo_rooty()+root.winfo_height()
        for widget in (app.status_widget, app.details_widget):
            assert widget.winfo_ismapped()
            assert widget.winfo_rooty()+widget.winfo_height() <= bottom
            assert widget.winfo_height() >= widget.winfo_reqheight()
        assert app.canvas.get_tk_widget().winfo_height() > 250
        assert app.view.get() == 'Земля и Луна', 'Opening a rotating checkpoint starts with the inner orbit'
    finally:
        app.close()


def test_status_and_diagnostics_remain_visible_at_default_window_size(tmp_path):
    run_gui_check('_check_window_layout', tmp_path)
