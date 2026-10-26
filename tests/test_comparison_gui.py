"""Actual Tk comparison journeys in fresh isolated Tcl interpreters."""
import pytest


def make_pair(tmp_path):
    from dataclasses import replace
    from solar_simulator.experiment import Settings, advance, create_experiment
    from solar_simulator.sandbox import branch_experiment
    from solar_simulator.simulation import Body
    from solar_simulator.trajectory import record_trajectory
    from solar_simulator.vector3 import Vector3
    seed = create_experiment([Body('free', 1., Vector3(3., 4., 5.), Vector3(2., -1., .5))],
                             Settings(10., integrator='dop853'))
    parent = advance(seed, 2)
    branch = branch_experiment(parent, replacements=(('free', replace(parent.bodies[0], velocity=Vector3(5., 3., -1.5))),))
    record_trajectory(seed, tmp_path/'parent', 80., packet_steps=2)
    record_trajectory(branch.child, tmp_path/'child', 60., packet_steps=2, parent_snapshot=branch.parent_snapshot)


def _check_comparison_window_and_export(tmp_path):
    import json
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    from solar_simulator.storage import to_document
    make_pair(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob('*.json')}
    root = tk.Tk()
    root.withdraw()
    app = Laboratory(root)
    created = []
    from solar_simulator.comparison_view import ComparisonViewer
    def open_view(*args,**kwargs):
        view = ComparisonViewer(*args,**kwargs)
        view.window.withdraw()
        created.append(view)
        return view
    def forbidden(*args, **kwargs):
        raise AssertionError('Comparison invoked solver')
    try:
        original = to_document(app.experiment)
        with patch('solar_simulator.app.filedialog.askdirectory', side_effect=[str(tmp_path/'parent'), str(tmp_path/'child')]), \
             patch('solar_simulator.app.messagebox.askyesnocancel', return_value=True), \
             patch('solar_simulator.comparison_view.ComparisonViewer', side_effect=open_view), \
             patch('solar_simulator.trajectory.advance_towards', side_effect=forbidden), \
             patch('solar_simulator.experiment.advance', side_effect=forbidden):
            loader=app._open_comparison()
            loader.future.result(timeout=10)
            loader._poll()
            assert len(created) == 1
            viewer = created[0]
            viewer.canvas.draw()
            renderer = viewer.canvas.get_renderer()
            boxes = [axis.get_tightbbox(renderer) for axis in (viewer.orbit, viewer.distance, viewer.velocity)]
            assert boxes[0].y0 > max(box.y1 for box in boxes[1:]), 'Plot labels overlap vertically'
            assert boxes[1].x1 < boxes[2].x0, 'Residual labels overlap horizontally'
            assert viewer.comparison.anchor_time == 20.
            assert viewer.comparison.event_side == 'after'
            viewer.slider.set(2)
            assert viewer.index == 2 and 't_parent=60' in viewer.status.get() and 't_child=40' in viewer.status.get()
            points = viewer.orbit.lines
            assert len(points) == 2 and list(points[0].get_xdata())[-1] == pytest.approx(123., abs=1e-10, rel=0.)
            assert list(points[1].get_xdata())[-1] == pytest.approx(243., abs=1e-10, rel=0.)
            assert list(viewer.distance.lines[0].get_ydata())[2] == pytest.approx(40*29**.5, abs=1e-10, rel=0.)
            viewer.reference.current(1)
            viewer.reference.event_generate('<<ComboboxSelected>>')
            root.update()
            assert viewer.samples[2]['bodies']['free']['distance_m'] == 0.
            assert viewer.samples[2]['bodies']['free']['distance_m_per_s'] == 0.
            viewer.plane.current(2)
            viewer.plane.event_generate('<<ComboboxSelected>>')
            root.update()
            assert viewer.orbit.get_xlabel() == 'Y, м'
            with patch('solar_simulator.comparison_view.filedialog.asksaveasfilename', return_value=str(tmp_path/'report.json')):
                viewer._export()
            doc = json.loads((tmp_path/'report.json').read_bytes())
            assert doc['reference'] == 'free' and len(doc['samples']) == 4
            with patch('solar_simulator.comparison_view.filedialog.asksaveasfilename', return_value=str(tmp_path/'child/manifest.json')), \
                 patch('solar_simulator.comparison_view.messagebox.showerror') as error:
                viewer._export()
            assert error.call_count == 1
        assert to_document(app.experiment) == original
        assert all(p.read_bytes() == raw for p, raw in before.items())
    finally:
        for viewer in created:
            viewer.close()
        app.close()


def _check_invalid_pair_and_cancel_leave_no_window(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory
    make_pair(tmp_path)
    root = tk.Tk()
    root.withdraw()
    app = Laboratory(root)
    try:
        with patch('solar_simulator.app.filedialog.askdirectory', side_effect=[str(tmp_path/'parent'), str(tmp_path/'parent')]), \
             patch('solar_simulator.app.messagebox.askyesnocancel', return_value=False), \
             patch('solar_simulator.trajectory_loader.messagebox.showerror') as error:
            loader=app._open_comparison()
            with pytest.raises(ValueError,match='bundle'):loader.future.result(timeout=10)
            loader._poll()
            assert error.call_count==1 and 'bundle' in error.call_args.args[1]
        assert not any(isinstance(w, tk.Toplevel) for w in root.winfo_children())
        with patch('solar_simulator.app.filedialog.askdirectory', side_effect=[str(tmp_path/'parent'), str(tmp_path/'child')]), \
             patch('solar_simulator.app.messagebox.askyesnocancel', return_value=None):
            app._open_comparison()
        assert not any(isinstance(w, tk.Toplevel) for w in root.winfo_children())
    finally:
        app.close()


@pytest.mark.parametrize('journey', ['_check_comparison_window_and_export', '_check_invalid_pair_and_cancel_leave_no_window'])
def test_real_comparison_journey(tmp_path, journey):
    from test_app_workflows import run_gui_check
    run_gui_check(journey, tmp_path, source=__file__)
