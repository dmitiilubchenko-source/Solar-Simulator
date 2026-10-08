from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from solar_simulator.accuracy import evolve_accurate
from solar_simulator.cli import main, report
from solar_simulator.diagnostics import model_invariants
from solar_simulator.ephemerides import solar_system
from solar_simulator.experiment import Settings, advance, create_experiment, preset, reset
from solar_simulator.oblateness import (PrescribedQuadrupole, acceleration, earth_j2,
    earth_moon_quadrupoles, orbital_torque, orientation_power, potential_energy, prepare)
from solar_simulator.orientation import (DURATION, PROFILE_SHA256, earth_pole,
                                         lunar_rotation, precession_matrix)
from solar_simulator.simulation import Body, G
from solar_simulator.storage import from_document, load, save, to_document
from solar_simulator.vector3 import Vector3

ROOT = Path(__file__).resolve().parents[1]


def test_erfa_precession_independent_published_oracle():
    # ERFA v2.0.1 t_erfa_c.c, t_ltp(), Julian epoch 1666.666.
    expected = [[.9967044141159213819,.07437801893193210840,.03237624409345603401],
        [-.07437802731819618167,.9972293894454533070,-.001205768842723593346],
        [-.03237622482766575399,-.001206286039697609008,.9994750246704010914]]
    assert np.allclose(precession_matrix((1666.666-2000)/100), expected, rtol=0, atol=1e-14)


def test_lunar_rotation_and_rate_against_independent_cspice():
    data = json.loads((ROOT/"docs/orientation-spice-reference.json").read_text())
    assert data["profile_sha256"] == PROFILE_SHA256
    assert hashlib.sha256((ROOT/"src/solar_simulator/data/orientation-de441-20261008.json").read_bytes()).hexdigest() == PROFILE_SHA256
    for row in data["samples"]:
        rotation, derivative = lunar_rotation(row["time_seconds"])
        assert np.allclose(rotation, row["rotation"], rtol=0, atol=3e-12)
        assert np.allclose(derivative, row["derivative_per_second"], rtol=0, atol=1e-17)
        assert np.allclose(rotation.T@rotation, np.eye(3), rtol=0, atol=2e-15)
        assert np.linalg.det(rotation) == pytest.approx(1, abs=2e-15)
        assert np.linalg.norm(derivative.T@rotation+rotation.T@derivative) < 1e-20


@pytest.mark.parametrize("time", [0., 32*86400., DURATION/2, DURATION])
def test_earth_pole_unit_and_rate(time):
    pole, derivative = earth_pole(time)
    assert np.linalg.norm(pole) == pytest.approx(1, abs=1e-15)
    assert abs(pole@derivative) < 1e-26
    assert pole[1] > .39  # ECLIPJ2000 northern pole has positive y.
    if 100 < time < DURATION-100:
        difference = (earth_pole(time+100)[0]-earth_pole(time-100)[0])/200
        assert np.allclose(difference, derivative, rtol=0, atol=5e-18)


@pytest.mark.parametrize("time", [-1., DURATION+1, float("nan"), float("inf"), True])
def test_orientation_rejects_extrapolation_and_invalid_time(time):
    for function in (earth_pole, lunar_rotation):
        with pytest.raises(ValueError):
            function(time)


def moon_figure():
    bodies, origin = solar_system(resolved_moon=True)
    return earth_moon_quadrupoles(bodies, origin)[1]


def test_c22_sign_and_unnormalized_factor_on_principal_axes():
    figure = replace(moon_figure(), coefficient=0.)
    rotation, _ = lunar_rotation(0.)
    radius = 1e8
    for axis, sign in ((0, -1), (1, 1), (2, 0)):
        r = radius*rotation[:, axis]
        bodies = [Body("Moon", 1e22, Vector3(0,0,0), Vector3(0,0,0)),
                  Body("target", 7e23, Vector3(*map(float, r)), Vector3(0,0,0))]
        a = acceleration(np.array([[0.,0.,0.], r]), np.array([b.mass for b in bodies]), prepare(bodies,(figure,)))
        expected = sign*9*G*bodies[0].mass*figure.reference_radius**2*figure.c22/radius**4*rotation[:,axis]
        assert np.allclose(a[1], expected, rtol=1e-13, atol=1e-25)
        assert np.linalg.norm(bodies[0].mass*a[0]+bodies[1].mass*a[1]) <= max(np.linalg.norm(bodies[1].mass*a[1])*1e-15, 1.)


def test_quadrupole_force_matches_complex_step_body_frame_potential():
    figure = moon_figure()
    time = 19*86400.
    rotation, _ = lunar_rotation(time)
    p = np.array([[1e8,2e8,-3e8],[-2e8,3e8,4e8],[2e8,-3e8,1e8]])
    masses = np.array([1e22,4e24,2e23])
    bodies = [Body(name,float(m),Vector3(*map(float, r)),Vector3(0,0,0))
              for name,m,r in zip(("Moon","a","b"),masses,p)]
    def independent_potential(positions):
        value = 0.
        for i in (1,2):
            x,y,z = rotation.T@(positions[i]-positions[0])
            r = np.sqrt(x*x+y*y+z*z)
            value += G*masses[0]*masses[i]*figure.reference_radius**2/r**3*(
                figure.coefficient*(3*(z/r)**2-1)/2-3*figure.c22*((x/r)**2-(y/r)**2))
        return value
    expected = np.zeros_like(p)
    for i in range(3):
        for j in range(3):
            shifted = p.astype(complex); shifted[i,j] += 1e-20j
            expected[i,j] = -np.imag(independent_potential(shifted))/1e-20/masses[i]
    actual = acceleration(p,masses,prepare(bodies,(figure,)),time)
    assert np.allclose(actual,expected,rtol=3e-14,atol=1e-25)
    assert potential_energy(bodies,(figure,),time) == pytest.approx(independent_potential(p),rel=3e-15)
    shift = np.array([1e10,-3e10,7e10])
    assert np.allclose(acceleration(p+shift,masses,prepare(bodies,(figure,)),time),actual,rtol=1e-14,atol=0)


def test_orientation_power_is_explicit_potential_derivative():
    initial, origin = solar_system(resolved_moon=True)
    figures = earth_moon_quadrupoles(initial,origin)
    p = np.array([[b.position.x,b.position.y,b.position.z] for b in initial])
    masses = np.array([b.mass for b in initial])
    time = 80*86400.
    power = orientation_power(p,masses,prepare(initial,figures),time)
    difference = (potential_energy(initial,figures,time+10)-potential_energy(initial,figures,time-10))/20
    assert power == pytest.approx(difference,rel=1e-7)


def test_orientation_power_equals_angular_velocity_dot_orbital_torque():
    figure = moon_figure()
    bodies = [Body("Moon",7.35e22,Vector3(1e10,-2e10,3e10),Vector3(0,0,0)),
              Body("Earth",5.97e24,Vector3(1e10+3e8,-2e10+2e8,3e10-1e8),Vector3(0,0,0))]
    time = 5*86400.
    rotation, derivative = lunar_rotation(time)
    generator = derivative @ rotation.T
    omega = np.array([generator[2,1],generator[0,2],generator[1,0]])
    torque = orbital_torque(bodies,(figure,),time)
    p = np.array([[b.position.x,b.position.y,b.position.z] for b in bodies])
    power = orientation_power(p,np.array([b.mass for b in bodies]),prepare(bodies,(figure,)),time)
    assert power == pytest.approx(omega @ np.array([torque.x,torque.y,torque.z]),rel=1e-14)


def test_prescribed_model_against_independent_scaled_rk45():
    from scripts.assess_orientation import independent_reference, sample
    initial,origin = solar_system(resolved_moon=True)
    figures = earth_moon_quadrupoles(initial,origin)
    times = np.linspace(0,2*86400.,5)
    reference,consistency = independent_reference(initial,figures,times)
    actual,_ = sample(initial,origin,times,figures)
    assert consistency < .1
    assert np.linalg.norm(actual[:,:,:3]-reference[:,:,:3],axis=2).max() < .1
    assert np.linalg.norm(actual[:,:,3:]-reference[:,:,3:],axis=2).max() < 1e-6


def test_newtonian_prescribed_figure_energy_balance_subtracts_work():
    figure = moon_figure()
    r = 1e8
    m1, m2 = 7.35e22, 5.97e24
    speed = np.sqrt(G*(m1+m2)/r)
    bodies = [Body("Moon",m1,Vector3(0,0,0),Vector3(0,0,0)),
              Body("Earth",m2,Vector3(r,0,0),Vector3(0,float(speed),0))]
    figures = (figure,)
    energy0 = model_invariants(bodies,figures=figures)[0]
    final, work = evolve_accurate(bodies,32*86400.,figures=figures,return_work=True,rtol=3e-14,
                                position_atol=1e-5,velocity_atol=1e-11)
    change = model_invariants(final,figures=figures,time=32*86400.)[0]-energy0
    assert abs(work) > 1e20
    assert abs((change-work)/energy0) < 2e-13
    # Work is ~1e-8 of orbital energy: energy subtraction amplifies its
    # relative numerical residual. Still removes >99.99% of the drift.
    assert abs(change-work) < abs(work)*1e-4


@pytest.mark.parametrize("physics", ["newtonian","eih-1pn"])
def test_checkpoint_resumes_orientation_time_and_accumulated_work(tmp_path,physics):
    initial, origin = solar_system(resolved_moon=True)
    figures = earth_moon_quadrupoles(initial,origin)
    state = create_experiment(initial,Settings(86400,integrator="dop853",physics=physics,figures=figures),origin=origin)
    whole = advance(state,32)
    partial = advance(state,16)
    save(partial,tmp_path/"q2.json")
    restored = load(tmp_path/"q2.json")
    assert restored.orientation_work == partial.orientation_work
    assert to_document(restored) == to_document(partial)
    resumed = advance(restored,16)
    assert max(a.position.distance_to(b.position) for a,b in zip(whole.bodies,resumed.bodies)) < 10
    assert abs(whole.orientation_work-resumed.orientation_work) < abs(whole.orientation_work)*1e-7
    assert reset(resumed).orientation_work == 0 and reset(resumed).time == 0
    values = report(resumed)
    assert values["energy_joules"] == model_invariants(resumed.bodies,physics,figures,resumed.time)[0]
    assert values["orientation_work_joules"] == resumed.orientation_work
    assert "energy budget subtracts" in values["conservation_scope"]
    assert not values["orbital_angular_momentum_conserved"]


def test_v6_fixed_j2_checkpoint_migrates_without_new_physics():
    state = preset("solar-system-moon")
    state = replace(state,settings=replace(state.settings,figures=earth_j2(state.bodies,state.origin)))
    document = to_document(state)
    document["schema_version"] = 6; del document["orientation_work"]
    before = deepcopy(document)
    restored = from_document(document)
    assert restored.settings == state.settings and restored.orientation_work == 0
    assert document == before


@pytest.mark.parametrize("field,value", [("orientation_work",True),("orientation_work",float("nan")),
    ("orientation_work",1.),("time",DURATION+1)])
def test_checkpoint_rejects_inconsistent_work_and_time(field,value):
    state = preset("solar-system-moon")
    state = replace(state,settings=replace(state.settings,figures=earth_moon_quadrupoles(state.bodies,state.origin)))
    document = to_document(state); document[field] = value
    with pytest.raises(ValueError):
        from_document(document)


def test_prescribed_profile_identity_origin_and_interval_guards():
    state = preset("solar-system-moon")
    figures = earth_moon_quadrupoles(state.bodies,state.origin)
    with pytest.raises(ValueError):
        replace(figures[1],profile_sha256="0"*64)
    with pytest.raises(ValueError):
        replace(figures[0],c22=.00001)
    with pytest.raises(ValueError):
        create_experiment(state.bodies,replace(state.settings,figures=figures))
    with pytest.raises(ValueError):
        create_experiment(state.bodies,replace(state.settings,figures=figures),origin=replace(state.origin,epoch_jd_tdb=2451545.))
    state = replace(state,settings=replace(state.settings,figures=figures,dt=DURATION+1))
    with pytest.raises(ValueError):
        advance(state,1)
    assert state.time == 0 and state.orientation_work == 0
    with pytest.raises(ValueError):
        from_document(dict(to_document(preset("sun-earth")),orientation_work=1.))


@pytest.mark.parametrize("option,count", [("earth-q2",1),("earth-moon-q2",2)])
def test_cli_prescribed_models_and_tolerance_comparison(tmp_path,capsys,option,count):
    path, final = tmp_path/"start.json",tmp_path/"final.json"
    assert main(["new","solar-system-moon",str(path),"--physics","eih-1pn","--figures",option]) == 0
    assert main(["run",str(path),str(final),"--steps","24"]) == 0
    assert len(load(final).settings.figures) == count and load(final).orientation_work != 0
    assert main(["converge",str(final),"--steps","24"]) == 0
    assert "orientation_work_joules" in capsys.readouterr().out
