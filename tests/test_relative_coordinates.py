"""Independent mechanics, frame restoration and checkpoint checks for pair coordinates."""
from copy import deepcopy
from dataclasses import replace
from math import cos, sin, sqrt, pi

import numpy as np
import pytest

from solar_simulator.accuracy import evolve_accurate
from solar_simulator.coordinates import prepare_pair
from solar_simulator.experiment import Settings, advance, create_experiment, preset, reset
from solar_simulator.simulation import Body, G, sun_earth
from solar_simulator.storage import from_document, to_document, save, load
from solar_simulator.vector3 import Vector3
from scripts.assess_resolved_moon import states


def test_pair_map_preserves_mechanics_and_nonselected_bodies():
    bodies = [Body(str(i),m,Vector3(i,2*i,-i),Vector3(0,0,0)) for i,m in enumerate((3.,7.,11.))]
    mapping = prepare_pair(bodies,("2","0"))  # Reverse, nonconsecutive indices.
    p = states(bodies)[:,:3]
    transformed = mapping.encode(p)
    assert np.array_equal(transformed[1],p[1])
    assert np.allclose(transformed[2],(11*p[2]+3*p[0])/14,rtol=0,atol=1e-15)
    assert np.array_equal(transformed[0],p[0]-p[2])
    assert np.allclose(mapping.decode(transformed),p,rtol=0,atol=5e-16)
    v = np.array([[9.,-3.,2.],[4.,1.,-8.],[-5.,6.,3.]])
    mapped = mapping.encode(v)
    momentum = 11*v[2]+3*v[0]
    assert np.allclose(14*mapped[2],momentum,atol=1e-14,rtol=0)
    kinetic = (11*np.dot(v[2],v[2])+3*np.dot(v[0],v[0]))/2
    decomposition = (14*np.dot(mapped[2],mapped[2])+(33/14)*np.dot(mapped[0],mapped[0]))/2
    assert decomposition == pytest.approx(kinetic,rel=2e-16)


def test_pair_vector_formed_before_common_offset_rounding():
    bodies,_ = sun_earth()
    mapping = prepare_pair(bodies,("Sun","Earth"))
    p = np.array([[0.,0.,0.],[.25,.5,.75]])
    encoded = mapping.encode(p,offset=np.full(3,1e16))
    assert np.array_equal(encoded[1],p[1]-p[0])
    assert not np.array_equal((p-1e16)[1]-(p-1e16)[0],encoded[1])


def test_large_masses_do_not_overflow_pair_weights():
    bodies = [Body(str(i),m,Vector3(i,0,0),Vector3(0,0,0)) for i,m in enumerate((1e308,5e307))]
    mapping = prepare_pair(bodies,("0","1"))
    assert mapping.first_fraction == pytest.approx(2/3)
    assert mapping.second_fraction == pytest.approx(1/3)
    with pytest.raises(ValueError,match="float64"):
        prepare_pair([replace(bodies[0],mass=5e-324),bodies[1]],("0","1"))


def test_pair_force_geometry_retains_small_vector_after_large_reconstruction():
    from solar_simulator.relativity import C, eih_acceleration, _eih_acceleration
    from solar_simulator.oblateness import FixedJ2, prepare, acceleration, orientation_power
    # Both reconstructed absolute positions round to the same float. The
    # independently represented pair separation remains a valid force input.
    relative=np.array([.25,.5,.75])
    p=np.array([[0.,0.,0.],relative])
    v=np.array([[20.,30.,40.],[-30.,5.,10.]])
    masses=np.array([3.,7.])
    reference=eih_acceleration(p,v,masses)
    large=np.full((2,3),1e16)
    actual=_eih_acceleration(large,v,masses,C,(0,1,relative))
    assert np.allclose(actual,reference,rtol=3e-16,atol=0)
    bodies=[Body(str(i),mass,Vector3(*p[i]),Vector3(*v[i])) for i,mass in enumerate(masses)]
    figures=(FixedJ2("0",.001,.01,(0.,0.,1.)),)
    prepared=prepare(bodies,figures)
    expected=acceleration(p,masses,prepared)
    result=acceleration(large,masses,prepared,_pair_displacement=(0,1,relative))
    assert np.allclose(result,expected,rtol=3e-16,atol=0)
    assert np.linalg.norm(np.sum(result*masses[:,None],axis=0))<1e-30
    assert orientation_power(large,masses,prepared,0.,_pair_displacement=(0,1,relative))==0


@pytest.mark.parametrize("pair",[("Sun",),["Sun","Earth"],("Sun","Sun"),("Sun",True),("Sun"," "),"Sun"])
def test_invalid_pair_option_rejected(pair):
    with pytest.raises(ValueError):
        Settings(1,integrator="dop853",relative_pair=pair)


def test_pair_requires_existing_names_and_compatible_solver():
    bodies,_ = sun_earth()
    with pytest.raises(ValueError,match="существующие"):
        create_experiment(bodies,Settings(1,integrator="dop853",relative_pair=("Earth","Moon")))
    for options in ({},{"backend":"rust","integrator":"verlet"}):
        with pytest.raises(ValueError,match="DOP853"):
            Settings(1,relative_pair=("Sun","Earth"),**options)
    spheres = preset("spheres")
    with pytest.raises(ValueError,match="точечные"):
        evolve_accurate(spheres.bodies,1,relative_pair=("A","B"))


@pytest.mark.parametrize("pair",[("Sun","Earth"),("Earth","Sun")])
def test_relative_pair_against_analytic_kepler_in_shifted_frame(pair):
    from scripts.assess_accuracy import kepler_relative
    initial,period = sun_earth(.6)
    shift,boost = Vector3(4e12,-2e12,3e12),Vector3(500,-800,300)
    shifted = [replace(b,position=b.position.add(shift),velocity=b.velocity.add(boost)) for b in initial]
    result = evolve_accurate(shifted,period*.75,relative_pair=pair)
    expected_r,expected_v = kepler_relative(.6,.75,period)
    assert result[1].position.subtract(result[0].position).distance_to(expected_r)<10
    assert result[1].velocity.subtract(result[0].velocity).distance_to(expected_v)<1e-5
    # Absolute output must retain the original origin and inertial drift.
    total = sum(b.mass for b in initial)
    centre = sum((b.mass*np.array([b.position.x,b.position.y,b.position.z]) for b in result))/total
    start_centre = sum((b.mass*np.array([b.position.x,b.position.y,b.position.z]) for b in shifted))/total
    drift = sum((b.mass*np.array([b.velocity.x,b.velocity.y,b.velocity.z]) for b in shifted))/total
    assert np.linalg.norm(centre-start_centre-drift*period*.75)<.01


def test_three_body_exact_solution_with_selected_pair():
    mass,radius = 1e24,1e9
    omega = sqrt(G*mass/(sqrt(3)*radius**3))
    duration = pi/(2*omega)
    initial = [Body(str(i),mass,Vector3(radius*cos(i*2*pi/3),radius*sin(i*2*pi/3),0),
        Vector3(-omega*radius*sin(i*2*pi/3),omega*radius*cos(i*2*pi/3),0)) for i in range(3)]
    result = evolve_accurate(initial,duration,relative_pair=("0","2"))
    for i,b in enumerate(result):
        angle = i*2*pi/3+pi/2
        assert b.position.distance_to(Vector3(radius*cos(angle),radius*sin(angle),0))<1


def test_pair_eih_restores_original_frame_velocities_against_independent_solver():
    from scipy.integrate import solve_ivp
    from scripts.assess_relativity import mercury_pair, independent_acceleration
    from solar_simulator.relativity import C
    initial,period,_ = mercury_pair()
    initial = [replace(b,velocity=b.velocity.add(Vector3(2e5,-1e5,3e4))) for b in initial]
    start = states(initial)
    centre = start[0,:3].copy()
    q = start.copy(); q[:,:3]-=centre
    masses = np.array([G*b.mass for b in initial])
    def rhs(t,y):
        state=y.reshape(2,6)
        return np.concatenate((state[:,3:],independent_acceleration(state[:,:3],state[:,3:],masses,C)),axis=1).ravel()
    duration=period/10
    reference=solve_ivp(rhs,(0,duration),q.ravel(),method="RK45",rtol=3e-14,atol=1e-9).y[:,-1].reshape(2,6)
    reference[:,:3]+=centre
    actual=states(evolve_accurate(initial,duration,physics="eih-1pn",relative_pair=("Sun","Mercury")))
    assert np.max(np.linalg.norm(actual[:,:3]-reference[:,:3],axis=1))<.2
    assert np.max(np.linalg.norm(actual[:,3:]-reference[:,3:],axis=1))<1e-6


def test_prescribed_pair_checkpoint_resume_reset_and_numerical_switch(tmp_path):
    from solar_simulator.oblateness import earth_moon_quadrupoles
    initial=preset("solar-system-moon")
    settings=replace(initial.settings,physics="eih-1pn",figures=earth_moon_quadrupoles(initial.bodies,initial.origin),
                     relative_pair=("Earth","Moon"))
    initial=create_experiment(initial.bodies,settings,origin=initial.origin)
    whole=advance(initial,48)
    partial=advance(initial,24)
    save(partial,tmp_path/"pair.json")
    restored=load(tmp_path/"pair.json")
    assert to_document(restored)==to_document(partial)
    resumed=advance(restored,24)
    assert np.max(np.linalg.norm(states(resumed.bodies)[:,:3]-states(whole.bodies)[:,:3],axis=1))<.01
    assert abs(resumed.orientation_work-whole.orientation_work)<1e14
    restarted=reset(resumed)
    assert restarted.settings.relative_pair==("Earth","Moon") and restarted.orientation_work==0
    # A numerical coordinate switch does not reset epoch, figures or accumulated work.
    switched=replace(partial,settings=replace(partial.settings,relative_pair=None))
    assert advance(switched,24).time==whole.time
    assert switched.orientation_work==partial.orientation_work


def test_v7_migration_preserves_equations_and_work_without_enabling_pair():
    from solar_simulator.oblateness import earth_moon_quadrupoles
    initial=preset("solar-system-moon")
    initial=replace(initial,settings=replace(initial.settings,physics="eih-1pn",figures=earth_moon_quadrupoles(initial.bodies,initial.origin)))
    document=to_document(advance(initial,1))
    document["schema_version"]=7
    del document["settings"]["relative_pair"]
    del document["settings"]["error_control"]
    original=deepcopy(document)
    restored=from_document(document)
    assert document==original
    assert restored.settings.relative_pair is None and restored.orientation_work==document["orientation_work"]
    assert restored.settings.physics=="eih-1pn" and len(restored.settings.figures)==2


@pytest.mark.parametrize("pair",[["Earth"],["Earth","Earth"],["Earth","missing"],["Earth",False],"Earth",("Earth","Moon")])
def test_v8_rejects_malformed_or_missing_pairs(pair):
    document=to_document(preset("solar-system-moon"))
    document["settings"]["relative_pair"]=pair
    with pytest.raises(ValueError):
        from_document(document)


def test_cli_pair_creation_run_and_convergence(tmp_path,capsys):
    import json
    from solar_simulator.cli import main
    source,target=tmp_path/"start.json",tmp_path/"end.json"
    assert main(["new","sun-earth",str(source),"--relative-pair","Sun","Earth","--dt","3600"])==0
    assert json.loads(capsys.readouterr().out)["relative_pair"]==["Sun","Earth"]
    assert main(["run",str(source),str(target),"--steps","24"])==0
    assert load(target).settings.relative_pair==("Sun","Earth")
    capsys.readouterr()
    assert main(["converge",str(target),"--steps","24"])==0
    comparison=json.loads(capsys.readouterr().out)
    assert comparison["relative_pair_comparison"]["bodies"]==["Sun","Earth"]
