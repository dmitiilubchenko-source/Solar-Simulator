"""Real editor widgets: cancel/failure preserve state; successful save forks."""


def _check_editor_bundle_journey(tmp_path):
    import tkinter as tk
    from tkinter import ttk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import advance
    from solar_simulator.sandbox import load_branch
    from solar_simulator.storage import to_document
    root = tk.Tk(); root.withdraw()
    app = Laboratory(root)
    errors = []
    try:
        app._set_experiment(advance(app.experiment, 3))
        original = app.experiment
        before = to_document(original)
        app.running = True
        try:
            app._edit()
        except ValueError:
            pass
        else:
            raise AssertionError("A running experiment must reject editing")
        app.running = False
        app._edit()
        dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
        fields = sorted((w for w in dialog.winfo_children() if type(w) is ttk.Entry),
                        key=lambda w: int(w.grid_info()["row"]))
        fields[1].delete(0, "end")
        fields[1].insert(0, str(original.bodies[0].mass*2))
        apply = next(w for w in dialog.winfo_children() if isinstance(w, ttk.Button))
        with patch("solar_simulator.app.filedialog.asksaveasfilename", return_value=""):
            apply.invoke()
        assert app.experiment is original and dialog.winfo_exists()
        path = tmp_path/"опыт с родителем.json"
        path.write_bytes(b"previous file")
        with patch("solar_simulator.app.filedialog.asksaveasfilename", return_value=str(path)), \
             patch("solar_simulator.storage.os.replace", side_effect=OSError("Controlled disk failure")), \
             patch("solar_simulator.app.messagebox.showerror", side_effect=lambda *a, **kw: errors.append(a)):
            apply.invoke()
        assert app.experiment is original and path.read_bytes() == b"previous file"
        assert len(errors) == 1 and dialog.winfo_exists()
        with patch("solar_simulator.app.filedialog.asksaveasfilename", return_value=str(path)):
            apply.invoke()
        child = to_document(app.experiment)
        assert child["time"] == 0 and child["origin"] is None
        assert child["bodies"][0]["mass"] == 2*before["bodies"][0]["mass"]
        branch = load_branch(path)
        assert to_document(branch.parent) == before
        assert to_document(branch.child) == child
        assert to_document(original) == before
        app._set_experiment(original)
        with patch("solar_simulator.app.filedialog.askopenfilename", return_value=str(path)):
            app._load()
        assert to_document(app.experiment) == child
        app._reset()
        assert to_document(app.experiment) == child
    finally:
        app.close()


def test_edit_cancel_disk_failure_fork_load_and_reset(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check("_check_editor_bundle_journey", tmp_path, source=__file__)
