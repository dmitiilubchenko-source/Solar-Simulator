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
