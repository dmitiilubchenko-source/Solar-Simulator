from pathlib import Path


def _check_parent_return(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import advance,preset
    from solar_simulator.sandbox import branch_experiment,save_branch
    from solar_simulator.storage import load,to_document
    from dataclasses import replace
    parent=advance(preset("sun-earth"),2)
    branch=branch_experiment(parent,replacements=(("Sun",replace(parent.bodies[0],mass=2*parent.bodies[0].mass)),))
    path=tmp_path/"branch.json";save_branch(branch,path)
    root=tk.Tk();root.withdraw();app=Laboratory(root)
    try:
        assert str(app.parent_button['state'])=='disabled'
        with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(path)):app._load()
        assert app.parent_snapshot==branch.parent_snapshot
        app.experiment=advance(app.experiment,1);current=to_document(app.experiment)
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=''):app._restore_parent()
        assert to_document(app.experiment)==current and app.parent_snapshot==branch.parent_snapshot
        checkpoint=tmp_path/'current.json';checkpoint.write_bytes(b'keep')
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(checkpoint)), \
             patch('solar_simulator.storage.os.replace',side_effect=OSError('disk failure')):
            try:app._restore_parent()
            except OSError:pass
            else:raise AssertionError('Failed write accepted')
        assert checkpoint.read_bytes()==b'keep' and to_document(app.experiment)==current
        app._reset();assert app.parent_snapshot==branch.parent_snapshot
        app.experiment=advance(app.experiment,1);current=to_document(app.experiment)
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(checkpoint)):app._restore_parent()
        from solar_simulator.branch_io import open_experiment
        saved,snapshot=open_experiment(checkpoint)
        assert to_document(saved)==current and snapshot==branch.parent_snapshot
        assert to_document(app.experiment)==to_document(parent)
        assert app.parent_snapshot is None and str(app.parent_button['state'])=='disabled'
        original=to_document(parent);app.experiment.bodies[0].position.x+=1
        assert to_document(parent)==original
    finally:app.close()


def test_real_gui_restore_parent_saves_current_and_preserves_state_on_cancel_and_write_error(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_parent_return',tmp_path,Path(__file__).resolve())
