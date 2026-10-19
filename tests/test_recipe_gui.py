"""The viewer audits provenance read-only and still opens legacy trajectories."""


def _check_recipe_button(tmp_path):
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.experiment import Settings, create_experiment
    from solar_simulator.simulation import Body
    from solar_simulator.trajectory import Trajectory, record_trajectory
    from solar_simulator.trajectory_view import TrajectoryViewer
    from solar_simulator.vector3 import Vector3
    state = create_experiment([Body('free', 1., Vector3(0, 0, 0), Vector3(1, 2, 3))], Settings(10.))
    record_trajectory(state, tmp_path/'source', 25.25, packet_steps=2)
    original = {path.name: path.read_bytes() for path in (tmp_path/'source').iterdir()}
    root = tk.Tk()
    root.withdraw()
    view = TrajectoryViewer(tk.Toplevel(root), Trajectory(tmp_path/'source'))
    view.window.withdraw()
    try:
        def forbidden(*args, **kwargs):
            raise AssertionError('Provenance inspection called solver')
        with patch('solar_simulator.trajectory.advance_towards', side_effect=forbidden), \
             patch('solar_simulator.experiment.advance', side_effect=forbidden), \
             patch('solar_simulator.trajectory_view.messagebox.showinfo') as message:
            view._recipe()
        assert message.call_count == 1 and 'совпадают' in message.call_args.args[1]
        assert original == {path.name: path.read_bytes() for path in (tmp_path/'source').iterdir()}
        (tmp_path/'source/recipe.json').unlink()
        with patch('solar_simulator.trajectory_view.messagebox.showerror') as message:
            view._recipe()
        assert message.call_count == 1 and 'нет recipe' in message.call_args.args[1]
        view._seek(2)
        assert view.player.state[0].time == 25.25
    finally:
        view.close()
        root.destroy()


def test_real_recipe_audit_and_legacy_viewer(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_recipe_button', tmp_path, source=__file__)
