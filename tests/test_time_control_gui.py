from pathlib import Path


def _check_target_journey(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import Settings, create_experiment
    from solar_simulator.simulation import Body
    from solar_simulator.storage import to_document
    from solar_simulator.time_control import advance_towards
    from solar_simulator.vector3 import Vector3
    initial=create_experiment([Body("free",1e20,Vector3(5.,6.,7.),Vector3(2.,-3.,4.))],
                              Settings(3.,integrator="dop853"))
    root=tk.Tk(); root.withdraw(); app=Laboratory(root,initial)
    try:
        app.batch.set("2"); app.target.set("nan"); app.dt.set("7")
        try: app._start_target()
        except ValueError: pass
        else: raise AssertionError("Invalid target must reject before applying settings")
        assert app.experiment is initial and not app.running
        app.dt.set("3"); app.target.set("10.25")
        app._start_target(); app._poll()
        future=app.future
        app._pause()
        assert app.future is future and "завершает пакет" in app.status.get()
        future.result(timeout=15); app._poll()
        assert app.experiment.time == 6. and app.future is None and not app.running
        path=tmp_path/"pause.json"
        with patch("solar_simulator.app.filedialog.asksaveasfilename",return_value=str(path)):
            app._save()
        app._reset()
        assert app.experiment.time == 0. and app.target_time is None
        with patch("solar_simulator.app.filedialog.askopenfilename",return_value=str(path)):
            app._load()
        assert app.experiment.time == 6. and app.target_time is None
        app._start_target(); app._poll(); app.future.result(timeout=15); app._poll()
        assert app.experiment.time == 10.25 and not app.running and app.future is None
        expected=advance_towards(advance_towards(initial,10.25,2),10.25,2)
        assert to_document(app.experiment) == to_document(expected)
        assert "цель 10.25" in app.status.get()
        before=app.experiment; app.target.set("1")
        try: app._start_target()
        except ValueError: pass
        else: raise AssertionError("Backward target accepted")
        assert app.experiment is before
        app.target.set("10.25"); app._start_target()
        assert not app.running and app.future is None
        app._start(); assert app.target_time is None
        app._poll(); app.future.result(timeout=15); app._pause(); app._poll()
        assert app.experiment.time == 16.25
    finally: app.close()


def test_real_gui_target_pause_save_load_resume_and_ordinary_playback(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check("_check_target_journey",tmp_path,Path(__file__).resolve())
