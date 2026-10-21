"""Loss prevention in real Tk, including failures before committing a replacement."""
import pytest


def _fixture(tmp_path):
    import tkinter as tk
    from dataclasses import replace
    from solar_simulator.app import Laboratory
    from solar_simulator.experiment import Settings,create_experiment,advance
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    from solar_simulator.sandbox import branch_experiment
    from solar_simulator.branch_io import save_experiment
    seed=create_experiment([Body('probe',1.,Vector3(0,0,0),Vector3(1,0,0))],Settings(1.))
    parent=advance(seed,10)
    branch=branch_experiment(parent,replacements=(('probe',replace(parent.bodies[0],mass=2.)),))
    current=advance(branch.child,3)
    incoming=tmp_path/'incoming.json';save_experiment(seed,incoming)
    root=tk.Tk();root.withdraw()
    app=Laboratory(root,current,parent_snapshot=branch.parent_snapshot)
    return app,current,branch.parent_snapshot,incoming


def _actions(app,incoming):
    return (app._new,app._reset,app._load,app._open_lunar_rotation,
            app._open_solar_sandbox,lambda:app._restore_recovery(incoming))


def _check_all_transitions_preserve_old_branch(tmp_path):
    from unittest.mock import patch
    from solar_simulator.branch_io import open_experiment
    from solar_simulator.storage import to_document
    from solar_simulator.recovery import list_recoveries
    app,current,parent,incoming=_fixture(tmp_path)
    try:
        assert not list_recoveries(), 'Initial construction does not save a recovery'
        for action in _actions(app,incoming):
            app._set_experiment(current,parent_snapshot=parent)
            before=len(list_recoveries())
            with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(incoming)):
                action()
            assert app.experiment is not current and len(list_recoveries())==before+1
            saved,snapshot=open_experiment(app.last_recovery_path)
            assert to_document(saved)==to_document(current) and snapshot==parent
            assert 'solar-replaced-' in str(app.last_recovery_path)
        # Recovery is usable by a new application instance, not just a mock writer.
        saved,snapshot=open_experiment(app.last_recovery_path)
        app.close()
        import tkinter as tk
        from solar_simulator.app import Laboratory
        root=tk.Tk();root.withdraw();app=Laboratory(root,saved,parent_snapshot=snapshot)
        assert to_document(app.experiment)==to_document(current) and app.parent_snapshot==parent
    finally:app.close()


def _check_failed_writes_preserve_state_and_plots(tmp_path):
    from unittest.mock import patch
    app,current,parent,incoming=_fixture(tmp_path)
    try:
        frames=tuple(app.frames);energies=tuple(app.energies)
        for action in _actions(app,incoming):
            with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(incoming)), \
                 patch('solar_simulator.recovery.save_recovery',side_effect=OSError('controlled disk failure')):
                with pytest.raises(OSError,match='controlled disk failure'):action()
            assert app.experiment is current and app.parent_snapshot==parent
            assert tuple(app.frames)==frames and tuple(app.energies)==energies
            assert app.last_recovery_path is None and not app.closed
    finally:app.close()


def _check_cancel_invalid_input_and_active_packet(tmp_path):
    from concurrent.futures import Future
    from dataclasses import replace
    from unittest.mock import patch
    app,current,parent,incoming=_fixture(tmp_path)
    try:
        with patch('solar_simulator.recovery.save_recovery') as saved:
            with patch('solar_simulator.app.filedialog.askopenfilename',return_value=''):app._load()
            incoming.write_text('{invalid JSON')
            with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(incoming)):
                with pytest.raises(ValueError):app._load()
            with pytest.raises(ValueError):app._replace_experiment(replace(current,time=float('nan')))
            app.future=Future()
            with pytest.raises(ValueError,match='пакета'):app._replace_experiment(current)
            app.future=None
            assert not saved.called and app.experiment is current and app.parent_snapshot==parent
    finally:
        app.future=None;app.close()


@pytest.mark.parametrize('journey',[
    '_check_all_transitions_preserve_old_branch',
    '_check_failed_writes_preserve_state_and_plots',
    '_check_cancel_invalid_input_and_active_packet'])
def test_real_experiment_replacement(journey,tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check(journey,tmp_path,source=__file__)
