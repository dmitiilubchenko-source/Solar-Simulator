"""Production native forces versus separate formula, Python and saved orbits."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest
native = pytest.importorskip('solar_native')
from solar_simulator.native_forces import prepare
from solar_simulator.relativity import C, _eih_acceleration
from solar_simulator.simulation import G
from solar_simulator.experiment import Settings, preset, advance, create_experiment
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from solar_simulator.storage import save, load
from scripts.independent_eih_rust import load_oracle
from scripts.fetch_asteroid_catalog import trial_system
from scripts.assess_resolved_moon import states


@pytest.mark.parametrize('count', [2, 3, 27, 354])
def test_native_total_and_amplified_pn_correction_against_two_independent_forces(count):
    rng = np.random.default_rng(847+count)
    oracle = load_oracle()
    for _ in range(5):
        p, v = rng.normal(size=(count,3))*10, rng.normal(size=(count,3))*.03
        mu = rng.uniform(.0002,.001,count)
        masses = mu/G
        force = prepare(masses)
        for pair in (None, (0,count-1,p[-1]-p[0]), (count-1,0,p[0]-p[-1])):
            for c in (300., C):
                actual = force(p,v,c,pair)
                python = _eih_acceleration(p,v,masses,c,pair)
                independent = oracle(p,v,mu,c,pair)
                assert np.allclose(actual,python,rtol=2e-14,atol=1e-18)
                assert np.allclose(actual,independent,rtol=2e-14,atol=1e-18)
            newton = force(p,v,None,pair)
            correction = force(p,v,300.,pair)-newton
            expected = _eih_acceleration(p,v,masses,300.,pair)-_eih_acceleration(p,v,masses,1e20,pair)
            assert np.max(np.linalg.norm(correction,axis=1)) > 1e-10*np.max(np.linalg.norm(newton,axis=1))
            assert np.allclose(correction,expected,rtol=2e-7,atol=2e-18)


def test_native_pair_override_resolves_positions_lost_in_absolute_float64():
    masses = np.array([1e20,1e18])
    p, v = np.full((2,3),1e30), np.zeros((2,3))
    f = prepare(masses)
    rho = np.array([1e8,2e8,-3e8])
    assert np.array_equal(f(p,v,None,(0,1,rho)),f(p,v,None,(1,0,-rho)))
    with pytest.raises(ValueError): f(p,v)


@pytest.mark.parametrize('change', ['mass', 'shape', 'nan', 'pair', 'same_pair', 'negative_pair', 'speed', 'strong', 'overflow'])
def test_native_force_rejects_invalid_and_out_of_domain_data(change):
    m, p, v = np.array([1e20,1e18]), np.array([[0.,0.,0.],[1e8,0.,0.]]), np.zeros((2,3))
    c, pair = C, None
    if change == 'mass': m[0] = 0.
    if change == 'shape': p = p[:1]
    if change == 'nan': p[0,0] = np.nan
    if change == 'pair': pair = (0,7,[1.,0.,0.])
    if change == 'same_pair': pair = (0,0,[1.,0.,0.])
    if change == 'negative_pair': pair = (-1,0,[1.,0.,0.])
    if change == 'speed': c = True
    if change == 'strong': v[0,0] = C*.02
    if change == 'overflow': c = 1e308
    with pytest.raises(ValueError): prepare(m)(p,v,c,pair)


def test_missing_or_stale_native_module_has_an_explicit_rebuild_message(monkeypatch):
    monkeypatch.setitem(sys.modules,'solar_native',SimpleNamespace())
    with pytest.raises(RuntimeError,match='build_native'): prepare([1.])
    monkeypatch.setitem(sys.modules,'solar_native',None)
    with pytest.raises(RuntimeError,match='build_native'): prepare([1.])


def test_native_force_is_thread_safe_and_does_not_mutate_inputs():
    p = np.array([[0.,0.,0.],[1e8,0.,0.]]);v=np.zeros((2,3));m=np.array([1e20,1e18])
    f=prepare(m);expected=f(p,v,C)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:f(p,v,C),range(8)))
    assert all(np.array_equal(r,expected) for r in results)
    assert np.array_equal(p,[[0.,0.,0.],[1e8,0.,0.]]) and np.all(v==0.)
    assert np.array_equal(m,[1e20,1e18])


def test_rust_dop853_preserves_figures_work_and_saved_relative_pair(tmp_path):
    initial=preset('solar-system-asteroids-full')
    figures=sun_earth_moon_quadrupoles(initial.bodies,initial.origin)
    settings=Settings(3600,backend='rust',integrator='dop853',physics='eih-1pn',figures=figures,
        relative_pair=('Earth','Moon'),rtol=3e-14,position_atol=1e-5,velocity_atol=1e-11)
    rust=create_experiment(initial.bodies,settings,origin=initial.origin)
    result=advance(rust,24)
    python=advance(replace(rust,settings=replace(settings,backend='python')),24)
    assert np.max(np.linalg.norm(states(result.bodies)[:,:3]-states(python.bodies)[:,:3],axis=1))<.01
    assert result.orientation_work == pytest.approx(python.orientation_work,rel=1e-10)
    file=tmp_path/'native.json';save(advance(rust,12),file);restored=load(file)
    assert restored.settings == settings and restored.origin == rust.origin
    resumed=advance(restored,12)
    assert np.max(np.linalg.norm(states(resumed.bodies)[:,:3]-states(result.bodies)[:,:3],axis=1))<.01
    from solar_simulator.storage import SCHEMA_VERSION
    assert json.loads(file.read_text())['schema_version']==SCHEMA_VERSION


def test_native_newton_dop853_kepler_and_cli(tmp_path,capsys):
    from solar_simulator.cli import main
    initial=preset('sun-earth')
    settings=replace(initial.settings,backend='rust',integrator='dop853',relative_pair=('Sun','Earth'))
    rust=advance(create_experiment(initial.bodies,settings),240)
    python=advance(create_experiment(initial.bodies,replace(settings,backend='python')),240)
    assert np.max(np.linalg.norm(states(rust.bodies)-states(python.bodies),axis=1))<.01
    file=tmp_path/'cli.json'
    assert main(['new','solar-system-asteroids-full',str(file),'--backend','rust','--physics','eih-1pn',
        '--figures','sun-earth-moon-q2','--relative-pair','Earth','Moon'])==0
    capsys.readouterr()
    assert load(file).settings.backend=='rust' and load(file).settings.integrator=='dop853'
    assert main(['run',str(file),str(tmp_path/'next.json'),'--steps','1'])==0
    assert json.loads(capsys.readouterr().out)['backend']=='rust'


@pytest.mark.parametrize('options', [['--physics','eih-1pn'],
    ['--figures','sun-earth-moon-q2'], ['--relative-pair','Earth','Moon']])
def test_rust_cli_selects_required_adaptive_integrator(options,tmp_path,capsys):
    from solar_simulator.cli import main
    file=tmp_path/'auto.json'
    assert main(['new','solar-system-asteroids-full',str(file),'--backend','rust',*options])==0
    capsys.readouterr()
    assert load(file).settings.integrator=='dop853'
    with pytest.raises(SystemExit) as error:
        main(['new','solar-system-asteroids-full',str(file),'--backend','rust',
            *options,'--integrator','verlet'])
    assert error.value.code==2


def test_native_eih_uses_original_inertial_velocities_in_translating_solver_frame():
    from solar_simulator.accuracy import evolve_accurate
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    initial=[Body('A',1e20,Vector3(0.,0.,0.),Vector3(5e5,2e5,-1e5)),
        Body('B',1e18,Vector3(1e8,2e8,-3e8),Vector3(5e5+10,2e5-20,-1e5+30))]
    options=dict(physics='eih-1pn',relative_pair=('A','B'),rtol=3e-14,
        position_atol=1e-5,velocity_atol=1e-11)
    python=evolve_accurate(initial,3600.,**options)
    rust=evolve_accurate(initial,3600.,backend='rust',**options)
    assert np.max(np.linalg.norm(states(rust)-states(python),axis=1))<.001
