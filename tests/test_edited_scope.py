"""Scientific scope survives editing, checkpoint/bundle IO and orbital export."""
import csv
from dataclasses import replace
from decimal import localcontext
import json

import numpy as np
import pytest

from scripts.assess_edited_scope import fixture,reference,trajectory,metrics
from scripts.assess_kepler_phase import decimal_relative
from scripts.assess_sandbox_limits import elliptic_reference
from scripts.assess_sandbox_planets import states
from scripts.newton_year import ROOT
from solar_simulator.branch_io import open_experiment
from solar_simulator.cli import report
from solar_simulator.experiment import advance,reset
from solar_simulator.sandbox import branch_experiment,save_branch,load_branch
from solar_simulator.simulation import Body
from solar_simulator.state_export import export_state
from solar_simulator.storage import load,save,to_document
from solar_simulator.vector3 import Vector3


@pytest.fixture(scope='module')
def strict_seed():
    return load(ROOT/'docs/solar-sandbox-strict-checkpoint.json')


def edit(parent,action):
    if action=='add':
        return dict(additions=(Body('New body',6e24,Vector3(1e13,2e12,3e11),Vector3(1e3,2e3,3e3)),))
    if action=='remove':return dict(removals=('Neptune',))
    body=next(b for b in parent.bodies if b.name==('Sun' if action=='mass' else 'Mercury'))
    if action=='mass':changed=replace(body,mass=2*body.mass)
    if action=='position':changed=replace(body,position=body.position.add(Vector3(1e6,-2e6,3e6)))
    if action=='velocity':changed=replace(body,velocity=body.velocity.add(Vector3(100.,-200.,300.)))
    return dict(replacements=((body.name,changed),))


@pytest.mark.parametrize('elapsed',[0,86400])
@pytest.mark.parametrize('action',['mass','position','velocity','add','remove'])
def test_edited_jpl_origin_does_not_return_through_io(strict_seed,tmp_path,elapsed,action):
    parent=advance(strict_seed,elapsed//3600)
    before=to_document(parent)
    branch=branch_experiment(parent,**edit(parent,action))
    assert branch.child.origin is None and branch.child.time==0
    assert branch.changes() and branch.child.settings==parent.settings
    path=tmp_path/'branch.json';save_branch(branch,path)
    child,snapshot=open_experiment(path)
    assert snapshot==branch.parent_snapshot and to_document(load_branch(path).parent)==before
    assert report(child)['origin'] is None and report(child)['epoch_jd_tdb'] is None
    checkpoint=tmp_path/'child.json';save(child,checkpoint)
    current=load(checkpoint);initial=to_document(current)
    continued=advance(current,1)
    assert to_document(continued)==to_document(advance(child,1))
    assert continued.origin is None and to_document(reset(continued))==initial
    csv_path=tmp_path/'child.csv';export_state(continued,csv_path)
    with csv_path.open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream))
    assert len(rows)==len(continued.bodies)
    assert all(row['epoch_jd_tdb']=='' and row['time_scale']=='elapsed SI seconds' for row in rows)
    assert json.loads(rows[0]['settings_json'])['physics']=='eih-1pn'
    assert to_document(parent)==before and to_document(branch.parent)==before


@pytest.mark.parametrize('case',['fast','mass','inside','coincident','remove-figure','remove-pair'])
def test_existing_domain_rejections_preserve_parent(strict_seed,case):
    before=to_document(strict_seed);sun=strict_seed.bodies[0]
    if case in ('remove-figure','remove-pair'):
        kwargs=dict(removals=('Sun' if case=='remove-figure' else 'Moon',))
    elif case=='mass':
        kwargs=dict(replacements=(('Sun',replace(sun,mass=sun.mass*1e9)),))
    else:
        position=sun.position.add(Vector3(1e13,0.,0.));velocity=Vector3(0.,0.,0.)
        if case=='fast':velocity=Vector3(1e8,0.,0.)
        if case=='inside':position=sun.position.add(Vector3(1e8,0.,0.))
        if case=='coincident':position=sun.position
        kwargs=dict(additions=(Body('Invalid',6e24,position,velocity),))
    with pytest.raises(ValueError):branch_experiment(strict_seed,**kwargs)
    assert to_document(strict_seed)==before


@pytest.mark.parametrize('kind',['prescribed','spin'])
def test_unsupported_orientation_is_explicit_and_preserves_parent(strict_seed,kind):
    if kind=='spin':
        from solar_simulator.application_profiles import lunar_rotation
        parent=lunar_rotation(backend='rust')
    else:
        from solar_simulator.oblateness import earth_moon_quadrupoles
        from solar_simulator.experiment import create_experiment
        settings=replace(strict_seed.settings,
            figures=earth_moon_quadrupoles(strict_seed.bodies,strict_seed.origin))
        parent=create_experiment(strict_seed.bodies,settings,origin=strict_seed.origin)
    before=to_document(parent)
    with pytest.raises(ValueError,match='Ветки не поддерживают'):branch_experiment(parent)
    assert to_document(parent)==before


def test_position_reference_uses_actual_initial_vector_outside_old_fixture_geometry():
    _,branch,_=fixture('position-edit','python');q=states(branch.child.bodies)
    expected,row=reference(branch.child,np.array([0.,3600.]))
    with localcontext() as context:
        context.prec=110
        actual=decimal_relative(q)
        assert expected[0]==(actual[:3],actual[3:])
    assert row['checks_passed']
    old,_,_=elliptic_reference([0.],branch.child.bodies)
    assert np.linalg.norm(old[0,:3]-(q[1,:3]-q[0,:3]))>1e9


@pytest.mark.parametrize('backend',['python','rust'])
def test_position_edit_dynamics_against_actual_ic_decimal_oracle(backend):
    _,branch,_=fixture('position-edit',backend);times=np.linspace(0.,7200.,33)
    expected,ref=reference(branch.child,times)
    values,stats=trajectory(branch.child,times)
    row=metrics(values,expected,np.array([b.mass for b in branch.child.bodies]))
    assert ref['checks_passed'] and stats['checkpoint_continue_exact']
    assert row['position_metres']<10. and row['velocity_m_per_s']<1e-5


@pytest.mark.parametrize('case',['shape','nan'])
def test_incomplete_or_nonfinite_comparison_is_rejected(case):
    _,branch,_=fixture('position-edit','python');times=np.array([0.,1.])
    expected,_=reference(branch.child,times)
    values=np.stack([states(branch.child.bodies)]*2)
    if case=='shape':values=values[:1]
    else:values[1,1,0]=np.nan
    with pytest.raises(ValueError,match='shape or finite'):
        metrics(values,expected,np.array([b.mass for b in branch.child.bodies]))


def test_cli_extract_export_preserve_child_scope(strict_seed,tmp_path,capsys):
    from solar_simulator.commands import main
    path=tmp_path/'branch.json';save_branch(branch_experiment(strict_seed,**edit(strict_seed,'mass')),path)
    child=tmp_path/'child.json'
    assert main(['branch',str(path),str(child),'--part','child'])==0
    assert json.loads(capsys.readouterr().out)['origin'] is None
    exported=tmp_path/'child.csv'
    assert main(['export-state',str(path),str(exported)])==0
    assert json.loads(capsys.readouterr().out)['bodies']==10
    with exported.open(encoding='utf-8',newline='') as stream:rows=list(csv.DictReader(stream))
    assert all(row['epoch_jd_tdb']=='' for row in rows)
