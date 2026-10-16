from pathlib import Path


def _check_removal(tmp_path):
    import tkinter as tk
    from tkinter import ttk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import advance
    from solar_simulator.sandbox import load_branch
    from solar_simulator.storage import to_document
    root=tk.Tk();root.withdraw();app=Laboratory(root)
    errors=[]
    try:
        parent=app.experiment;before=to_document(parent)
        app._remove_body();root.update()
        dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        choice=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Combobox))
        button=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button))
        choice.set('Sun')
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=''):button.invoke()
        assert app.experiment is parent and dialog.winfo_exists()
        path=tmp_path/'removed.json';path.write_bytes(b'keep')
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(path)), \
             patch('solar_simulator.storage.os.replace',side_effect=OSError('disk failure')), \
             patch('solar_simulator.app.messagebox.showerror',side_effect=lambda *a,**kw:errors.append(a)):
            button.invoke()
        assert app.experiment is parent and path.read_bytes()==b'keep' and len(errors)==1
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(path)):button.invoke()
        assert len(app.experiment.bodies)==1 and app.experiment.bodies[0].name=='Earth'
        assert to_document(parent)==before and to_document(load_branch(path).parent)==before
        assert app.parent_snapshot is not None
        body=app.experiment.bodies[0];result=advance(app.experiment,2).bodies[0]
        expected=body.position.add(body.velocity.multiply(2*app.experiment.settings.dt))
        assert result.position.distance_to(expected)<1e-4
        app._remove_body();root.update()
        dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        button=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button))
        with patch('solar_simulator.app.messagebox.showerror',side_effect=lambda *a,**kw:errors.append(a)), \
             patch('solar_simulator.app.filedialog.asksaveasfilename') as picker:button.invoke()
        assert not picker.called and len(app.experiment.bodies)==1
        dialog.destroy()
        app._open_solar_sandbox();qualified=app.experiment
        app._remove_body();root.update()
        dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        choice=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Combobox));choice.set('Sun')
        button=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button))
        with patch('solar_simulator.app.messagebox.showerror',side_effect=lambda *a,**kw:errors.append(a)), \
             patch('solar_simulator.app.filedialog.asksaveasfilename') as picker:button.invoke()
        assert not picker.called and app.experiment is qualified
    finally:app.close()


def test_actual_removal_dialog_preserves_parent_and_keeps_model_guards(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_removal',tmp_path,Path(__file__).resolve())
