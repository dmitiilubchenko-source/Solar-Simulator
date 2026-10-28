"""Opt-in inspection is read-only and never certifies arbitrary trajectories."""
import json
from dataclasses import replace

import pytest

from solar_simulator import cli,commands
from solar_simulator.experiment import preset
from solar_simulator.storage import save,to_document
from solar_simulator.inspection import report


def test_opt_in_extends_inspect_without_changing_legacy_json(tmp_path,capsys):
    state=preset('sun-earth',eccentricity=.99)
    path=tmp_path/'checkpoint.json';save(state,path);before=path.read_bytes()
    assert commands.main(['inspect',str(path)])==0
    original=json.loads(capsys.readouterr().out)
    assert original==cli.report(state)
    assert commands.main(['inspect',str(path),'--reliability'])==0
    extended=json.loads(capsys.readouterr().out)
    detail=extended.pop('numerical_reliability')
    assert extended==original and path.read_bytes()==before
    assert detail['accuracy']['global_position_error_metres'] is None
    assert detail['accuracy']['jpl_residual_metres'] is None
    assert detail['qualification']['current_trajectory_certified'] is False


@pytest.mark.parametrize('factory',[
    lambda:preset('solar-system'),
    lambda:preset('solar-system-moon'),
    lambda:__import__('solar_simulator.solar_profiles',fromlist=['solar_sandbox']).solar_sandbox(profile='strict'),
    lambda:preset('sun-earth',eccentricity=.99),
])
def test_report_only_reads_existing_state_and_preserves_SI(factory,monkeypatch):
    state=factory();before=to_document(state)
    def forbidden(*args,**kwargs):raise AssertionError('Inspection must never integrate')
    monkeypatch.setattr('solar_simulator.experiment.advance',forbidden)
    monkeypatch.setattr('solar_simulator.accuracy.evolve_accurate',forbidden)
    monkeypatch.setattr('scipy.integrate.solve_ivp',forbidden)
    summary=report(state);detail=summary['numerical_reliability']
    assert to_document(state)==before
    assert detail['units']==dict(mass='kg',position='m',velocity='m/s',time='s',energy='J',
        momentum='kg*m/s',angular_momentum='kg*m^2/s')
    assert detail['invariants']['energy']['value']==summary['energy_joules']
    assert detail['invariants']['momentum']['value']==summary['momentum']
    assert detail['invariants']['energy_budget']['residual_joules']==summary['energy_budget_residual_joules']
    controls=detail['execution']['adaptive_controls']
    if state.settings.integrator=='dop853':
        assert controls['rtol']==state.settings.rtol
        assert controls['position_atol_metres']==state.settings.position_atol
        assert controls['velocity_atol_m_per_s']==state.settings.velocity_atol
        assert controls['error_control']==state.settings.error_control
        assert controls['relative_pair']==(list(state.settings.relative_pair) if state.settings.relative_pair else None)
    else:assert controls is None
    assert detail['time_and_packets']['last_packet_steps'] is None
    assert detail['time_and_packets']['output_cadence_seconds'] is None
    assert not detail['qualification']['current_trajectory_certified']
    assert detail['accuracy']['global_position_error_metres'] is None


def test_changed_mass_and_unknown_system_never_receive_qualification():
    from solar_simulator.solar_profiles import solar_sandbox
    from solar_simulator.sandbox import branch_experiment
    original=solar_sandbox(profile='strict');before=to_document(original)
    edited=branch_experiment(original,replacements=((original.bodies[0].name,replace(original.bodies[0],mass=original.bodies[0].mass*2)),)).child
    detail=report(edited)['numerical_reliability']
    assert detail['qualification']['input_profile']=='custom'
    assert not detail['qualification']['current_factory_input_settings_match']
    assert not detail['qualification']['current_trajectory_certified']
    assert to_document(original)==before
    from solar_simulator.experiment import create_experiment,Settings
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    unknown=create_experiment([Body('user',12.,Vector3(1,2,3),Vector3(4,5,6))],Settings(2))
    assert report(unknown)['numerical_reliability']['qualification']['input_profile']=='custom'


def test_restored_checkpoint_and_branch_have_the_same_diagnostics(tmp_path):
    from solar_simulator.storage import load
    from solar_simulator.sandbox import branch_experiment,save_branch
    from solar_simulator.branch_io import open_experiment
    state=preset('sun-earth',eccentricity=.99);path=tmp_path/'state.json';save(state,path)
    assert report(load(path))==report(state)
    child=branch_experiment(state,replacements=((state.bodies[0].name,replace(state.bodies[0],mass=state.bodies[0].mass*2)),))
    target=tmp_path/'branch.json';save_branch(child,target);before=target.read_bytes()
    restored,parent=open_experiment(target)
    assert parent is not None and report(restored)==report(child.child) and target.read_bytes()==before


def test_missing_native_does_not_prevent_state_diagnostics(monkeypatch):
    state=preset('sun-earth',backend='rust',eccentricity=.99)
    state=replace(state,settings=replace(state.settings,integrator='dop853'))
    before=to_document(state)
    def missing(*args):raise ModuleNotFoundError('injected missing native')
    monkeypatch.setattr('solar_simulator.recipe._native',missing)
    result=report(state);native=result['numerical_reliability']['execution']['native']
    assert native['required'] and native['status']=='unavailable'
    assert native['required_api']=='point_acceleration' and to_document(state)==before
    assert result['numerical_reliability']['execution']['past_execution_verified'] is False


def test_python_backend_does_not_probe_native_and_verlet_hides_unused_tolerances(monkeypatch):
    def forbidden(*args):raise AssertionError('Python inspection needs no native')
    monkeypatch.setattr('solar_simulator.recipe._native',forbidden)
    state=preset('sun-earth');detail=report(state)['numerical_reliability']
    assert detail['execution']['native']['status']=='not_required'
    assert detail['execution']['adaptive_controls'] is None
    assert detail['time_and_packets']['internal_step_seconds'] is None
    assert detail['time_and_packets']['configured_physical_step_seconds']==state.settings.dt


def test_newton_energy_and_momentum_against_hand_computed_values():
    from solar_simulator.simulation import Body,G
    from solar_simulator.experiment import Settings,create_experiment
    from solar_simulator.vector3 import Vector3
    bodies=[Body('A',2.,Vector3(0,0,0),Vector3(1,0,0)),Body('B',3.,Vector3(4,0,0),Vector3(0,2,0))]
    detail=report(create_experiment(bodies,Settings(1)))['numerical_reliability']
    assert detail['invariants']['energy']['value']==pytest.approx(7-G*6/4)
    assert detail['invariants']['momentum']['value']==[2.,6.,0.]
    assert detail['invariants']['angular_momentum']['value']==[0.,0.,24.]


@pytest.mark.parametrize('physics',['newtonian','eih-1pn'])
def test_fixed_figures_and_1pn_are_not_described_as_plain_conserved_orbit(physics):
    from solar_simulator.solar_profiles import solar_sandbox
    from solar_simulator.experiment import create_experiment
    seed=solar_sandbox(profile='strict');state=create_experiment(seed.bodies,replace(seed.settings,physics=physics),origin=seed.origin)
    detail=report(state)['numerical_reliability']
    assert detail['model']['id'].endswith('-fixed-j2')
    assert detail['invariants']['angular_momentum']['status']=='not_conserved_with_prescribed_axes'
    if physics=='eih-1pn':
        assert detail['invariants']['energy']['status']=='approximate_1pn_budget'
        assert 'Noether' in detail['invariants']['energy']['basis']
        assert any('figure/c' in text for text in detail['model']['limitations'])
    else:assert detail['invariants']['momentum']['status']=='conservative_total'


@pytest.mark.parametrize('physics',['newtonian','eih-1pn'])
def test_prescribed_orientation_requires_work_corrected_energy(physics):
    from solar_simulator.oblateness import earth_moon_quadrupoles
    from solar_simulator.experiment import create_experiment
    seed=preset('solar-system-moon')
    figures=earth_moon_quadrupoles(seed.bodies,seed.origin)
    state=create_experiment(seed.bodies,replace(seed.settings,physics=physics,figures=figures,integrator='dop853'),origin=seed.origin)
    detail=report(state)['numerical_reliability']
    assert detail['model']['id'].endswith('-prescribed-q2')
    expected='approximate_1pn_orientation_work_corrected_budget' if physics=='eih-1pn' else 'orientation_work_corrected_budget'
    assert detail['invariants']['energy']['status']==expected
    assert detail['invariants']['angular_momentum']['status']=='not_conserved_with_prescribed_axes'


def test_dynamic_rotation_uses_total_rigid_energy_and_angular_momentum():
    from solar_simulator.rotation import RigidFigure
    from solar_simulator.nbody_rotation import RotationState
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    from solar_simulator.experiment import create_experiment,Settings
    figure=RigidFigure(1e15,(2e20,2.5e20,3e20),1000.)
    rotation=RotationState('figure',figure,(1.,0.,0.,0.),(0.,0.,1e18),1e-13,1e5)
    bodies=[Body('figure',figure.mass,Vector3(0,0,0),Vector3(0,0,0)),Body('point',2e14,Vector3(12000,0,0),Vector3(0,2.55,0))]
    state=create_experiment(bodies,Settings(50,integrator='dop853'),rotations=(rotation,))
    detail=report(state)['numerical_reliability']
    assert detail['model']['id']=='newtonian-dynamic-q2'
    assert detail['invariants']['angular_momentum']['status']=='conservative_orbit_plus_dynamic_spin'
    assert detail['invariants']['angular_momentum']['value'][2]==pytest.approx(7.12e18)
    assert detail['execution']['adaptive_controls']['effective_error_norm'].startswith('RotationDOP853')
    assert detail['execution']['adaptive_controls']['rotation_tolerances'][0]['momentum_atol_kg_m2_s']==1e5


def test_contact_energy_is_a_ledger_not_a_mechanical_energy_guarantee():
    state=preset('spheres');detail=report(state)['numerical_reliability']
    assert detail['model']['id']=='newtonian-contacts'
    assert detail['invariants']['energy']['status']=='event_corrected_budget'
    assert detail['execution']['adaptive_controls'] is None


def test_1pn_without_figures_uses_noether_energy_not_newtonian_energy():
    from solar_simulator.experiment import create_experiment
    from solar_simulator.simulation import total_energy
    seed=preset('sun-earth')
    state=create_experiment(seed.bodies,replace(seed.settings,integrator='dop853',physics='eih-1pn'))
    detail=report(state)['numerical_reliability']
    assert detail['invariants']['energy']['value']!=total_energy(state.bodies)
    assert detail['invariants']['momentum']['status']=='approximate_1pn_noether'
    assert detail['invariants']['angular_momentum']['status']=='approximate_1pn_noether'
    assert '1PN' in detail['invariants']['center_of_mass_interpretation']


def test_existing_375_and_376_states_do_not_turn_into_new_accuracy_claims():
    from pathlib import Path
    import numpy as np
    from solar_simulator.vector3 import Vector3
    from solar_simulator.solar_profiles import solar_sandbox
    root=Path(__file__).resolve().parents[1]
    cases=[]
    original=solar_sandbox(profile='strict')
    with np.load(root/'scripts/validation/current-runtime-375.npz',allow_pickle=False) as data:
        values=data['current_python_strict20_values']
        cases.append((original,values[-1],31557600.))
    from scripts.check_runtime_reliability376 import seed_from,PROTOCOL,read
    protocol=read(PROTOCOL);job=next(j for j in protocol['jobs'] if j['id']=='high99-peri__python__strict__relative')
    case=next(c for c in protocol['cases'] if c['id']==job['case'])
    with np.load(root/'scripts/validation/runtime-reliability-376.npz',allow_pickle=False) as data:
        cases.append((seed_from(case,job),data[job['id']+'__states'][-1],case['epochs'][-1]))
    for initial,values,time in cases:
        bodies=[replace(b,position=Vector3(*map(float,row[:3])),velocity=Vector3(*map(float,row[3:]))) for b,row in zip(initial.bodies,values)]
        state=replace(initial,bodies=bodies,time=time);before=to_document(state)
        result=report(state);detail=result['numerical_reliability']
        assert detail['qualification']['current_trajectory_certified'] is False
        assert detail['accuracy']['global_position_error_metres'] is None
        assert detail['accuracy']['jpl_residual_metres'] is None
        assert detail['invariants']['energy']['value']==cli.report(state)['energy_joules']
        assert to_document(state)==before


def test_inspect_help_exposes_the_opt_in_flag(capsys):
    with pytest.raises(SystemExit) as exc:commands.main(['inspect','--help'])
    assert exc.value.code==0 and '--reliability' in capsys.readouterr().out


def test_matching_initial_profile_cannot_certify_an_edited_later_state():
    from solar_simulator.solar_profiles import solar_sandbox
    from solar_simulator.experiment import copy_bodies
    state=solar_sandbox(profile='strict');bodies=copy_bodies(state.bodies)
    bodies[0].velocity.x+=1.
    altered=replace(state,bodies=bodies,time=10.)
    detail=report(altered)['numerical_reliability']
    assert detail['qualification']['input_profile']=='strict'
    assert not detail['qualification']['current_trajectory_certified']
    assert not detail['execution']['past_execution_verified']
    assert detail['accuracy']['global_velocity_error_m_per_s'] is None


def test_fractional_terminal_step_is_not_reported_as_the_nominal_Verlet_step():
    from solar_simulator.experiment import create_experiment,Settings
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    from solar_simulator.time_control import advance_towards
    # Exact inertial motion, not another orbital experiment. The last physical
    # interval is1.25s, while the checkpoint retains the configured3s step.
    state=create_experiment([Body('free',2.,Vector3(0,0,0),Vector3(1,0,0))],Settings(3))
    state=advance_towards(state,1.25,1)
    assert state.time==1.25 and state.settings.dt==3
    packet=report(state)['numerical_reliability']['time_and_packets']
    assert packet['internal_step_seconds'] is None
    assert packet['configured_physical_step_seconds']==3


def test_factory_input_match_is_not_confused_with_the_qualification_time_horizon():
    from solar_simulator.solar_profiles import solar_sandbox,YEAR_SECONDS
    # No integration: inspect an otherwise unchanged checkpoint beyond the
    # measured horizon. Matching initial settings cannot certify this epoch.
    state=replace(solar_sandbox(profile='strict'),time=2*YEAR_SECONDS)
    qualification=report(state)['numerical_reliability']['qualification']
    assert qualification['input_profile']=='strict'
    assert qualification['current_factory_input_settings_match'] is True
    assert qualification['current_trajectory_certified'] is False
