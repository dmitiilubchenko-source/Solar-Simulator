"""Real editors: independent known vectors, native continuation, atomic failures."""
import pytest


def select(root, combo, index):
    combo.current(index)
    combo.event_generate('<<ComboboxSelected>>')
    root.update()


def editor(root, app, name):
    import tkinter as tk
    from tkinter import ttk
    app._edit()
    dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
    combo = next(w for w in dialog.winfo_children() if type(w) is ttk.Combobox)
    select(root, combo, list(combo['values']).index(name))
    return dialog, dialog.body_fields, next(w for w in dialog.winfo_children() if type(w) is ttk.Button)


def seed(backend='python'):
    from solar_simulator.experiment import Settings, create_experiment
    from solar_simulator.simulation import Body, EARTH_MASS, SUN_MASS
    from solar_simulator.vector3 import Vector3
    return create_experiment([
        Body('Center', SUN_MASS, Vector3(10000., -20000., 30000.), Vector3(2000., -3000., 5000.)),
        Body('Target', EARTH_MASS, Vector3(1e11, 2e10, 3e10), Vector3(20000., -1000., 0.),
             spin=Vector3(1., 2., 3.))], Settings(10., backend=backend, integrator='dop853'))


def _check_equivalent(tmp_path, backend):
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.sandbox import _canonical, branch_experiment, load_branch
    from solar_simulator.simulation import Body
    from solar_simulator.storage import to_document
    from solar_simulator.time_control import advance_towards
    from solar_simulator.vector3 import Vector3
    parent = seed(backend)
    before = to_document(parent)
    expected_body = Body('Target', 1.19444e25, Vector3(149597880700., 74798915350., -37399437675.),
                         Vector3(14000., -6000., 5500.), spin=Vector3(1., 2., 3.))
    expected = branch_experiment(parent, replacements=(('Target', expected_body),))
    root = tk.Tk()
    root.withdraw()
    app = Laboratory(root, parent)
    children = []
    try:
        for convenient in (False, True):
            app._set_experiment(parent)
            dialog, fields, apply = editor(root, app, 'Target')
            if convenient:
                select(root, fields.mass_unit, 1)
                select(root, fields.length_unit, 2)
                select(root, fields.speed_unit, 1)
                select(root, fields.reference, 1)  # Center, original parent snapshot.
                values = dict(mass='2', x='1', y='.5', z='-.25', vx='12', vy='-3', vz='.5')
            else:
                values = dict(mass='1.19444e25', x='149597880700', y='74798915350', z='-37399437675',
                              vx='14000', vy='-6000', vz='5500')
            for key, value in values.items():
                fields.variables[key].set(value)
            path = tmp_path/('convenient.json' if convenient else 'SI.json')
            if convenient:
                with patch('solar_simulator.app.filedialog.asksaveasfilename', return_value=''):
                    apply.invoke()
                assert app.experiment is parent and dialog.winfo_exists()
                path.write_bytes(b'original user file')
                with patch('solar_simulator.app.filedialog.asksaveasfilename', return_value=str(path)), \
                     patch('solar_simulator.storage.os.replace', side_effect=OSError('controlled disk error')), \
                     patch('solar_simulator.app.messagebox.showerror') as error:
                    apply.invoke()
                assert error.call_count == 1 and path.read_bytes() == b'original user file'
                assert app.experiment is parent and dialog.winfo_exists()
            with patch('solar_simulator.app.filedialog.asksaveasfilename', return_value=str(path)):
                apply.invoke()
            assert _canonical(to_document(app.experiment)) == _canonical(to_document(expected.child))
            assert to_document(load_branch(path).parent) == before
            children.append(app.experiment)
        assert _canonical(to_document(advance_towards(children[0], 20., 2))) == _canonical(
            to_document(advance_towards(children[1], 20., 2)))
        assert to_document(parent) == before
    finally:
        app.close()


def _check_equivalent_python(tmp_path):
    _check_equivalent(tmp_path, 'python')


def _check_equivalent_rust(tmp_path):
    _check_equivalent(tmp_path, 'rust')


def _check_switching_and_pending_edits(tmp_path):
    import tkinter as tk
    from solar_simulator.app import Laboratory
    from solar_simulator.sandbox import _canonical, branch_experiment, to_branch_document
    from solar_simulator.solar_profiles import solar_sandbox
    parent = solar_sandbox(profile='strict')
    root = tk.Tk()
    root.withdraw()
    app = Laboratory(root, parent)
    try:
        dialog, fields, _ = editor(root, app, 'Moon')
        old = next(body for body in parent.bodies if body.name == 'Moon')
        expected = _canonical(to_branch_document(branch_experiment(parent)))
        for cycle in range(10):
            select(root, fields.mass_unit, cycle % 3)
            select(root, fields.length_unit, cycle % 3)
            select(root, fields.speed_unit, cycle % 2)
            select(root, fields.reference, (cycle % len(parent.bodies))+1)
            read = fields.read(spin=old.spin)
            actual = branch_experiment(parent, replacements=(('Moon', read),))
            assert _canonical(to_branch_document(actual)) == expected
        # New partial edits are converted once, then retained exactly too.
        select(root, fields.mass_unit, 1)
        fields.variables['mass'].set('1.25')
        edited = fields.read(spin=old.spin)
        expected = _canonical(to_branch_document(branch_experiment(parent, replacements=(('Moon', edited),))))
        for cycle in range(8):
            select(root, fields.mass_unit, cycle % 3)
            select(root, fields.length_unit, cycle % 3)
            read = fields.read(spin=old.spin)
            assert _canonical(to_branch_document(branch_experiment(parent, replacements=(('Moon', read),)))) == expected
        dialog.destroy()
        from solar_simulator.experiment import Settings, create_experiment
        from solar_simulator.simulation import Body
        from solar_simulator.vector3 import Vector3
        signed = create_experiment([Body('signed', 1., Vector3(-0., 2., 3.), Vector3(4., -0., 6.))], Settings(1.))
        app._set_experiment(signed)
        dialog, fields, _ = editor(root, app, 'signed')
        select(root, fields.length_unit, 2)
        select(root, fields.speed_unit, 1)
        result = fields.read()
        assert result.position.x.hex() == (-0.).hex() and result.velocity.y.hex() == (-0.).hex()
        dialog.destroy()
    finally:
        app.close()


def _check_partial_invalid_and_stale_input(tmp_path):
    import tkinter as tk
    from tkinter import ttk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import advance
    root = tk.Tk()
    root.withdraw()
    parent = seed()
    app = Laboratory(root, parent)
    try:
        app._add_body()
        dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
        fields = dialog.body_fields
        for combo, index in ((fields.mass_unit, 2), (fields.length_unit, 1), (fields.speed_unit, 1), (fields.reference, 1)):
            select(root, combo, index)
        assert all(fields.variables[key].get() == '' for key in ('x', 'y', 'z', 'vx', 'vy', 'vz'))
        fields.variables['x'].set('12')
        fields.variables['y'].set('oops')
        old_values = {key: value.get() for key, value in fields.variables.items()}
        context = fields.context
        with patch('solar_simulator.body_fields.messagebox.showerror') as error:
            select(root, fields.length_unit, 2)
        assert error.call_count == 1 and fields.context == context and fields.length_unit.get() == 'км'
        assert {key: value.get() for key, value in fields.variables.items()} == old_values
        template = next(w for w in dialog.winfo_children() if type(w) is ttk.Combobox)
        select(root, template, 1)
        assert fields.variables['y'].get() == 'oops' and fields.variables['x'].get() == '12'
        assert fields.variables['mass'].get() == '1'  # Solar template in teaching solar units.
        apply = next(w for w in dialog.winfo_children() if type(w) is ttk.Button)
        with patch('solar_simulator.app.messagebox.showerror') as error, \
             patch('solar_simulator.app.filedialog.asksaveasfilename') as save:
            apply.invoke()
        assert error.call_count == 1 and not save.called and app.experiment is parent
        dialog.destroy()
        dialog, fields, apply = editor(root, app, 'Target')
        changed = advance(parent, 1)
        app._set_experiment(changed)
        with patch('solar_simulator.app.messagebox.showerror') as error, \
             patch('solar_simulator.app.filedialog.asksaveasfilename') as save:
            apply.invoke()
        assert error.call_count == 1 and 'изменился' in error.call_args.args[1]
        assert not save.called and app.experiment is changed
        dialog.destroy()
    finally:
        app.close()


def _check_add_relative_body(tmp_path):
    import tkinter as tk
    from tkinter import ttk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.sandbox import load_branch
    from solar_simulator.storage import to_document
    parent = seed()
    root = tk.Tk()
    root.withdraw()
    app = Laboratory(root, parent)
    try:
        app._add_body()
        dialog = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
        fields = dialog.body_fields
        select(root, fields.reference, 1)
        select(root, fields.length_unit, 1)
        select(root, fields.speed_unit, 1)
        for key, value in dict(name='Added', x='100', y='-200', z='300', vx='1', vy='2', vz='3').items():
            fields.variables[key].set(value)
        apply = next(w for w in dialog.winfo_children() if type(w) is ttk.Button)
        path = tmp_path/'added.json'
        with patch('solar_simulator.app.filedialog.asksaveasfilename', return_value=str(path)):
            apply.invoke()
        body = app.experiment.bodies[-1]
        assert (body.position.x, body.position.y, body.position.z) == (110000., -220000., 330000.)
        assert (body.velocity.x, body.velocity.y, body.velocity.z) == (3000., -1000., 8000.)
        assert body.radius == 0. and to_document(load_branch(path).parent) == to_document(parent)
    finally:
        app.close()


def _check_unrepresentable_display_and_inplace_change(tmp_path):
    import tkinter as tk
    from dataclasses import replace
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import advance, create_experiment
    initial = seed()
    parent = advance(create_experiment([initial.bodies[0], replace(initial.bodies[1], mass=1e-300)], initial.settings), 1)
    root = tk.Tk()
    root.withdraw()
    app = Laboratory(root, parent)
    try:
        dialog, fields, apply = editor(root, app, 'Target')
        values = {key: value.get() for key, value in fields.variables.items()}
        with patch('solar_simulator.body_fields.messagebox.showerror') as error:
            select(root, fields.mass_unit, 2)
        assert error.call_count == 1 and fields.mass_unit.get() == 'кг'
        assert {key: value.get() for key, value in fields.variables.items()} == values
        assert fields.read().mass == 1e-300
        parent.bodies[0].position.x += 1000.
        with patch('solar_simulator.app.messagebox.showerror') as error, \
             patch('solar_simulator.app.filedialog.asksaveasfilename') as save:
            apply.invoke()
        assert error.call_count == 1 and 'изменился' in error.call_args.args[1] and not save.called
        dialog.destroy()
    finally:
        app.close()


@pytest.mark.parametrize('journey', ['_check_equivalent_python', '_check_equivalent_rust',
    '_check_switching_and_pending_edits', '_check_partial_invalid_and_stale_input', '_check_add_relative_body',
    '_check_unrepresentable_display_and_inplace_change'])
def test_real_unit_editor_journey(tmp_path, journey):
    from test_app_workflows import run_gui_check
    run_gui_check(journey, tmp_path, source=__file__)
