"""Actual Tk refusal. Former GUI journey kept in product-before418-tests.zip."""
from pathlib import Path


def _check_two_q2(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.storage import to_document
    source=Path(__file__).resolve().parents[1]/"src/solar_simulator/data/two-q2-demo380.json"
    before=source.read_bytes()
    root=tk.Tk()
    app=Laboratory(root)
    try:
        initial=to_document(app.experiment)
        with patch("solar_simulator.app.filedialog.askopenfilename",return_value=str(source)):
            try:app._load()
            except ValueError as error:assert "не более одного" in str(error)
            else:raise AssertionError("Two-figure file accepted")
        assert to_document(app.experiment)==initial and source.read_bytes()==before
        widgets=[root]
        while widgets:
            widget=widgets.pop()
            if "text" in widget.keys():
                assert "Две Q2" not in str(widget.cget("text"))
            widgets.extend(widget.winfo_children())
    finally:
        app.close()


def test_two_q2_gui_load_refused_without_state_change(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check("_check_two_q2",tmp_path,source=Path(__file__).resolve())
