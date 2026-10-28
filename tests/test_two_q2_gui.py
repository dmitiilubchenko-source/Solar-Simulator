"""Existing GUI loads/advances/saves the headless two-Q2 model, no new editor."""
from pathlib import Path


def _check_two_q2(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    from scripts.two_q2_fixture380 import fixture
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import create_experiment,advance
    from solar_simulator.storage import save,load,to_document
    b,r,s=fixture();initial=create_experiment(b,s,rotations=r)
    path=tmp_path/'input.json';save(initial,path)
    root=tk.Tk();root.withdraw();app=Laboratory(root)
    try:
        with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(path)):app._load()
        assert to_document(app.experiment)==to_document(initial)
        app._submit(1);app.future.result(timeout=10);app._poll()
        assert to_document(app.experiment)==to_document(advance(initial,1))
        output=tmp_path/'output.json'
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(output)):app._save()
        assert to_document(load(output))==to_document(app.experiment)
        app._reset();assert to_document(app.experiment)==to_document(initial)
    finally:app.close()


def test_two_q2_gui_load_advance_save_reset(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_two_q2',tmp_path,source=Path(__file__).resolve())
