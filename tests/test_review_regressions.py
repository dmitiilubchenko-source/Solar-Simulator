"""User-visible regressions from the independent18October review."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from solar_simulator import cli,commands
from solar_simulator.app import Laboratory
from solar_simulator.branch_io import open_experiment,parent_experiment
from solar_simulator.contacts import run_until_contact
from solar_simulator.experiment import Settings,advance,create_experiment,preset
from solar_simulator.sandbox import branch_experiment,save_branch
from solar_simulator.simulation import Body
from solar_simulator.storage import to_document
from solar_simulator.time_control import advance_towards
from solar_simulator.vector3 import Vector3


def branch_file(tmp_path,backend='python'):
    parent=advance(preset('sun-earth',backend=backend),2)
    branch=branch_experiment(parent,replacements=(('Sun',replace(parent.bodies[0],mass=2*parent.bodies[0].mass)),))
    path=tmp_path/'branch.json';save_branch(branch,path)
    return path,branch


@pytest.mark.parametrize('changed_settings',[False,True])
def test_gui_save_over_original_branch_keeps_parent_after_continuation(tmp_path,changed_settings):
    path,branch=branch_file(tmp_path)
    state,snapshot=open_experiment(path)
    if changed_settings:state=replace(state,settings=replace(state.settings,dt=state.settings.dt/2))
    state=advance(state,2)
    app=SimpleNamespace(root=None,experiment=state,parent_snapshot=snapshot)
    with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(path)):
        Laboratory._save(app)
    loaded,parent=open_experiment(path)
    assert parent==branch.parent_snapshot
    assert to_document(parent_experiment(parent))==to_document(branch.parent)
    assert to_document(loaded)==to_document(state)
    assert json.loads(path.read_bytes())['version']==(2 if changed_settings else 1)


@pytest.mark.parametrize('command',['inspect','converge'])
def test_legacy_read_only_cli_accepts_branch_and_preserves_file(tmp_path,capsys,command):
    path,_=branch_file(tmp_path);before=path.read_bytes()
    args=[command,str(path)]+(['--steps','1'] if command=='converge' else [])
    assert cli.main(args)==0
    assert json.loads(capsys.readouterr().out)
    assert path.read_bytes()==before


@pytest.mark.parametrize('command',['run','run-until'])
@pytest.mark.parametrize('backend',['python','rust'])
def test_cli_continues_branch_with_parent_and_explicit_backend_change(tmp_path,capsys,command,backend):
    if backend=='rust':pytest.importorskip('solar_native')
    path,branch=branch_file(tmp_path,backend=backend if command=='run-until' else 'python')
    before=path.read_bytes();output=tmp_path/'continued.json'
    if command=='run':
        assert cli.main(['run',str(path),str(output),'--steps','2','--backend',backend])==0
        expected=advance(replace(branch.child,settings=replace(branch.child.settings,backend=backend)),2)
    else:
        assert commands.main(['run-until',str(path),str(output),'--time',str(2*branch.child.settings.dt)])==0
        expected=advance(branch.child,2)
    capsys.readouterr()
    actual,snapshot=open_experiment(output)
    assert snapshot==branch.parent_snapshot and to_document(actual)==to_document(expected)
    assert path.read_bytes()==before


def test_gui_cli_passes_parent_snapshot_to_launcher(tmp_path):
    path,branch=branch_file(tmp_path)
    with patch('solar_simulator.app.launch') as launch:
        assert cli.main(['gui',str(path)])==0
    args,kwargs=launch.call_args
    assert to_document(args[0])==to_document(branch.child)
    assert kwargs['parent_snapshot']==branch.parent_snapshot


@pytest.mark.parametrize('backend',['python','rust'])
def test_fractional_step_with_radius_finishes_at_exact_target_and_is_idempotent(backend):
    if backend=='rust':pytest.importorskip('solar_native')
    state=create_experiment([Body('free',1.,Vector3(0.,0.,0.),Vector3(1.,0.,0.),1.)],Settings(.1,backend=backend))
    result=advance_towards(state,2.,20)
    assert result.time==2. and not result.halted
    assert result.bodies[0].position.x==pytest.approx(2.,abs=1e-14)
    assert advance_towards(result,2.,20) is result
    raw=run_until_contact(state.bodies,.1,20,backend=backend)
    assert raw.time==.1*20 and raw.contact is None


@pytest.mark.parametrize('backend',['python','rust'])
def test_fractional_packet_contact_keeps_real_time_before_target(backend):
    if backend=='rust':pytest.importorskip('solar_native')
    bodies=[Body('left',1e-20,Vector3(-2.95,0.,0.),Vector3(1.,0.,0.),1.),
            Body('right',1e-20,Vector3(2.95,0.,0.),Vector3(-1.,0.,0.),1.)]
    result=advance_towards(create_experiment(bodies,Settings(.1,backend=backend)),2.,20)
    assert result.halted and result.time<2.
    assert result.time==result.events[-1].time==pytest.approx(1.95,abs=2e-12)


def _real_branch_save_and_restore(tmp_path):
    import tkinter as tk
    path,branch=branch_file(tmp_path)
    root=tk.Tk();root.withdraw();app=Laboratory(root)
    try:
        with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(path)):app._load()
        app.dt.set(str(app.experiment.settings.dt/2));app._settings()
        app.experiment=advance(app.experiment,2);before=to_document(app.experiment)
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(path)):app._save()
        with patch('solar_simulator.app.filedialog.askopenfilename',return_value=str(path)):app._load()
        assert app.parent_snapshot==branch.parent_snapshot
        assert to_document(app.experiment)==before
        with patch('solar_simulator.app.filedialog.asksaveasfilename',return_value=str(path)):app._restore_parent()
        child,parent=open_experiment(path)
        assert to_document(child)==before and parent==branch.parent_snapshot
        assert to_document(app.experiment)==to_document(branch.parent) and app.parent_snapshot is None
    finally:app.close()


def test_real_gui_branch_load_continue_save_reopen_restore(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_real_branch_save_and_restore',tmp_path,Path(__file__).resolve())
