"""Интеграционная проверка Tk: поток, пауза, сброс, смена проекции."""
import time

import pytest

tk=pytest.importorskip("tkinter")


def test_laboratory_worker_pause_reset_and_render(tmp_path):
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import preset
    try:
        root=tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"Tk display unavailable: {error}")
    root.withdraw()
    app=Laboratory(root,preset("spheres"))
    try:
        app._submit(10)
        deadline=time.monotonic()+10
        while app.future is not None and time.monotonic()<deadline:
            root.update()
            time.sleep(.01)
        assert app.future is None
        assert app.experiment.time==pytest.approx(.5)
        app.plane.set("XZ")
        app.reference.set("Тело: A")
        app._draw()
        app.figure.savefig(tmp_path/"laboratory.png")
        assert (tmp_path/"laboratory.png").stat().st_size>1000
        app._start()
        app._pause()
        assert not app.running
        app._reset()
        assert app.experiment.time==0 and len(app.frames)==1
        # Смена состава тел не должна смешивать старые индексы траекторий.
        from solar_simulator.experiment import advance
        app.mode.set("merge")
        app._settings()
        app.experiment=advance(app.experiment,1000)
        app._record()
        app._draw()
        assert len(app.experiment.bodies)==1
        assert "A+B" in app.frames[-1]
    finally:
        app.close()


def _check_accuracy_controls(tmp_path):
    from solar_simulator.app import Laboratory
    from solar_simulator.storage import save, load
    try:
        root=tk.Tk()
    except tk.TclError as error:
        pytest.skip(f"Tk display unavailable: {error}")
    root.withdraw()
    app=Laboratory(root)
    try:
        assert app.integrator.get()=="dop853"
        app.scenario.set("solar-system")
        app.physics.set("eih-1pn")
        app._new()
        assert len(app.experiment.bodies)==9 and app.experiment.origin is not None
        assert "DE441" in app.model_info.get()
        app.rtol.set("3e-14")
        app._submit(20)
        deadline=time.monotonic()+10
        while app.future is not None and time.monotonic()<deadline:
            root.update()
            time.sleep(.01)
        assert app.future is None and app.experiment.time>0
        assert app.experiment.settings.rtol==3e-14
        assert app.experiment.settings.physics=="eih-1pn"
        save(app.experiment,tmp_path/"accurate.json")
        app._set_experiment(load(tmp_path/"accurate.json"))
        assert app.integrator.get()=="dop853" and float(app.rtol.get())==3e-14
        assert app.physics.get()=="eih-1pn"
        assert "1PN" in app.energy.get_ylabel()
        app.physics.set("newtonian")
        with pytest.raises(ValueError,match="Смена физики"):
            app._settings()
        app.scenario.set("solar-system-moon")
        app.physics.set("eih-1pn")
        app._new()
        assert len(app.experiment.bodies)==10 and "Луна отдельно" in app.model_info.get()
        app.reference.set("Тело: Earth")
        app._submit(24)
        deadline=time.monotonic()+10
        while app.future is not None and time.monotonic()<deadline:
            root.update()
            time.sleep(.01)
        assert app.future is None and app.experiment.time>0
        save(app.experiment,tmp_path/"moon.json")
        app._set_experiment(load(tmp_path/"moon.json"))
        assert len(app.experiment.bodies)==10 and app.experiment.settings.physics=="eih-1pn"
        app._reset()
        app.figures.set("earth-j2")
        app._settings()
        assert app.experiment.settings.figures[0].body=="Earth"
        app._submit(24)
        deadline=time.monotonic()+10
        while app.future is not None and time.monotonic()<deadline:
            root.update()
            time.sleep(.01)
        assert app.future is None and app.experiment.time>0
        save(app.experiment,tmp_path/"j2.json")
        app._set_experiment(load(tmp_path/"j2.json"))
        assert app.figures.get()=="saved" and len(app.experiment.settings.figures)==1
        app.figures.set("none")
        with pytest.raises(ValueError,match="Смена физики"):
            app._settings()
        app._reset()
        app.figures.set("earth-moon-q2")
        app._settings()
        assert len(app.experiment.settings.figures)==2
        app._submit(24)
        deadline=time.monotonic()+10
        while app.future is not None and time.monotonic()<deadline:
            root.update()
            time.sleep(.01)
        assert app.future is None and app.experiment.orientation_work!=0
        save(app.experiment,tmp_path/"q2.json")
        app._set_experiment(load(tmp_path/"q2.json"))
        assert app.figures.get()=="saved" and len(app.experiment.settings.figures)==2
        assert "работа" in app.details.get()
        with pytest.raises(ValueError,match="Редактирование"):
            app._edit()
    finally:
        app.close()


def test_accuracy_controls_worker_and_checkpoint(tmp_path):
    # This Windows Tcl runtime cannot reliably create a second interpreter
    # after destroying the first. A fresh process also checks clean startup.
    import subprocess
    import sys
    from pathlib import Path
    code = """
import importlib.util, sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('app_checks',sys.argv[1])
module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
module._check_accuracy_controls(Path(sys.argv[2]))
"""
    result=subprocess.run([sys.executable,"-B","-c",code,str(Path(__file__).resolve()),str(tmp_path)],
                          capture_output=True,text=True,timeout=20)
    assert result.returncode==0, result.stdout+result.stderr
