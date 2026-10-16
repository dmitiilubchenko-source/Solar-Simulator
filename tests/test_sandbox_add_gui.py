"""A real GUI body addition must reproduce the explicit headless branch."""


def _check_add_body_journey(tmp_path):
    import tkinter as tk
    from tkinter import ttk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import advance
    from solar_simulator.sandbox import branch_experiment, load_branch
    from solar_simulator.simulation import Body
    from solar_simulator.storage import to_document
    from solar_simulator.vector3 import Vector3
    root=tk.Tk();root.withdraw()
    app=Laboratory(root)
    errors=[]
    try:
        app._open_solar_sandbox()
        assert len(app.experiment.bodies)==10 and app.experiment.settings.physics=="eih-1pn"
        assert len(app.experiment.settings.figures)==2
        parent=app.experiment;before=to_document(parent)
        app._add_body()
        dialog=next(w for w in root.winfo_children() if isinstance(w,tk.Toplevel))
        entries=sorted((w for w in dialog.winfo_children() if type(w) is ttk.Entry),
                       key=lambda w:int(w.grid_info()["row"]))
        assert len(entries)==8 and all(not w.get() for w in entries[2:])
        combo=next(w for w in dialog.winfo_children() if type(w) is ttk.Combobox)
        from solar_simulator.simulation import SUN_MASS, EARTH_MASS
        combo.set(combo["values"][1]);combo.event_generate("<<ComboboxSelected>>");root.update()
        assert float(entries[1].get())==SUN_MASS and entries[0].get().startswith("Звезда")
        combo.set(combo["values"][0]);combo.event_generate("<<ComboboxSelected>>");root.update()
        assert float(entries[1].get())==EARTH_MASS and all(not w.get() for w in entries[2:])
        button=next(w for w in dialog.winfo_children() if isinstance(w,ttk.Button))
        def fill(values):
            for entry,value in zip(entries,values):entry.delete(0,"end");entry.insert(0,str(value))
        def apply_with_error(values):
            fill(values)
            with patch("solar_simulator.app.messagebox.showerror",side_effect=lambda *a,**kw:errors.append(a)), \
                 patch("solar_simulator.app.filedialog.asksaveasfilename") as save_dialog:
                button.invoke()
            assert app.experiment is parent and not save_dialog.called
        # Duplicate, singularity, nonfinite and weak-field/exterior rejection.
        apply_with_error(("Sun",1e24,1e13,0,0,0,0,0))
        sun=parent.bodies[0]
        apply_with_error(("Coincident",1e24,sun.position.x,sun.position.y,sun.position.z,0,0,0))
        apply_with_error(("Not finite",float("nan"),1e13,0,0,0,0,0))
        apply_with_error(("Too fast",1e24,1e13,0,0,1e8,0,0))
        apply_with_error(("Inside Sun",1e24,sun.position.x+1e8,sun.position.y,sun.position.z,0,0,0))
        assert "радиус" in errors[-1][1].lower()
        assert len(errors)==5
        values=("My planet",6e24,1e13,2e12,3e11,1e3,2e3,3e3)
        fill(values)
        with patch("solar_simulator.app.filedialog.asksaveasfilename",return_value=""):
            button.invoke()
        assert app.experiment is parent and dialog.winfo_exists()
        path=tmp_path/"добавление тела.json"
        path.write_bytes(b"old file")
        with patch("solar_simulator.app.filedialog.asksaveasfilename",return_value=str(path)), \
             patch("solar_simulator.storage.os.replace",side_effect=OSError("Disk failure")), \
             patch("solar_simulator.app.messagebox.showerror",side_effect=lambda *a,**kw:errors.append(a)):
            button.invoke()
        assert app.experiment is parent and path.read_bytes()==b"old file"
        expected=branch_experiment(parent,additions=(Body(values[0],values[1],Vector3(*values[2:5]),Vector3(*values[5:])),))
        with patch("solar_simulator.app.filedialog.asksaveasfilename",return_value=str(path)):
            button.invoke()
        assert to_document(app.experiment)==to_document(expected.child)
        assert to_document(load_branch(path).parent)==before
        assert to_document(parent)==before
        assert "Тело: My planet" in app.reference_widget["values"]
        assert len(app.experiment.bodies)==11 and app.experiment.origin is None
        continued=advance(app.experiment,1)
        assert to_document(continued)==to_document(advance(expected.child,1))
        app.running=True
        try:app._add_body()
        except ValueError:pass
        else:raise AssertionError("Running add must be rejected")
        app.running=False
        app._open_lunar_rotation()
        try:app._add_body()
        except ValueError:pass
        else:raise AssertionError("Dynamic rotation add must be rejected")
    finally:app.close()


def test_add_body_errors_cancel_write_and_headless_equivalence(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check("_check_add_body_journey",tmp_path,source=__file__)
