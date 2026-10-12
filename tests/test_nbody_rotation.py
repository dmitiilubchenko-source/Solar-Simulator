"""Conservative N-body contract, force identities and persistence behavior."""
from dataclasses import replace
from copy import deepcopy

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from solar_simulator.nbody_rotation import (RotationState, RotationDOP853, correction,
    integrate, invariants, lunar_initial)
from solar_simulator.rotation import RigidFigure, rotation_matrix, integrate as integrate_pair
from solar_simulator.simulation import Body, G
from solar_simulator.vector3 import Vector3
from solar_simulator.experiment import Settings, create_experiment, advance, reset
from solar_simulator.ephemerides import solar_system
from solar_simulator.storage import to_document, from_document, save, load
from solar_simulator.cli import main, report


def model():
    figure = RigidFigure(1e15, (2e20, 2.5e20, 3e20), 1000.)
    q = np.roll(Rotation.from_rotvec([.3, -.2, .4]).as_quat(), 1)
    s = rotation_matrix(q)@(np.array(figure.moments)*[.0001, -.0002, .002])
    rotation = RotationState("figure", figure, tuple(q), tuple(s), 1e-13, float(np.linalg.norm(s)*1e-13))
    bodies = [Body("figure",figure.mass,Vector3(0,0,0),Vector3(0,0,0)),
              Body("point",2e14,Vector3(12000,0,0),Vector3(0,2.55,0))]
    settings = Settings(50., integrator="dop853", rtol=1e-11, position_atol=1e-7,
        velocity_atol=1e-11, relative_pair=("figure","point"))
    return create_experiment(bodies, settings, rotations=(rotation,))


def test_nbody_q2_force_gradient_torque_and_solar_reaction():
    state = model(); rotation = state.rotations[0]
    bodies = state.bodies+[Body("sun",5e15,Vector3(-50000,20000,15000),Vector3(0,0,0))]
    p = np.array([[b.position.x,b.position.y,b.position.z] for b in bodies]); m = np.array([b.mass for b in bodies])
    a, torque, energy = correction(p,m,0,rotation.figure,rotation.quaternion)
    float_field = correction(p.astype(float),m,0,rotation.figure,rotation.quaternion)
    assert np.array_equal(a,float_field[0]) and np.linalg.norm(a)>0
    p=p.astype(float)  # Finite-difference perturbations must not be truncated.
    forces = a*m[:,None]
    assert np.linalg.norm(forces.sum(axis=0))/np.linalg.norm(forces) < 1e-14
    assert np.linalg.norm(np.sum(np.cross(p,forces),axis=0)+torque)/np.linalg.norm(torque) < 1e-13
    # Independent MacCullagh I form, not the runtime tensor expression.
    r = p[1:]-p[0]; d = np.linalg.norm(r,axis=1); n = r/d[:,None]
    matrix = Rotation.from_quat(np.roll(rotation.quaternion,-1)).as_matrix()
    body_n = n@matrix
    expected = G*np.sum(m[1:]*(3*np.sum(body_n**2*np.array(rotation.figure.moments),axis=1)
        -sum(rotation.figure.moments))/(2*d**3))
    assert energy == pytest.approx(expected,rel=2e-13)
    for i in range(3):
        for k in range(3):
            changed = p.copy(); changed[i,k] += .01
            plus = correction(changed,m,0,rotation.figure,rotation.quaternion)[2]
            changed[i,k] -= .02
            minus = correction(changed,m,0,rotation.figure,rotation.quaternion)[2]
            assert -(plus-minus)/.02 == pytest.approx(forces[i,k],rel=2e-6,abs=np.linalg.norm(forces)*1e-8)


@pytest.mark.parametrize("backend",["python","rust"])
@pytest.mark.parametrize("pair",[("figure","point"),("point","figure"),None])
def test_two_body_limit_and_full_invariants(backend,pair):
    if backend=="rust":pytest.importorskip("solar_native")
    state = model(); rotation = state.rotations[0]
    times = np.linspace(0,20000,41)
    snapshots = integrate(state.bodies,state.rotations,times,rtol=1e-11,position_atol=1e-7,
        velocity_atol=1e-11,relative_pair=pair,backend=backend,max_step=100)
    initial = np.r_[12000.,0,0,0,2.55,0,rotation.quaternion,rotation.angular_momentum]
    ref = integrate_pair(rotation.figure,initial,times,point_mass=2e14,rtol=3e-13,
        atol=np.r_[[1e-9]*3,[1e-13]*3,[1e-14]*4,[rotation.momentum_atol*.03]*3],max_step=50)
    e0,p0,l0 = invariants(*snapshots[0])
    for (bodies,rotations), expected in zip(snapshots,ref):
        r = bodies[1].position.subtract(bodies[0].position)
        assert np.linalg.norm(np.array([r.x,r.y,r.z])-expected[:3])/12000 < 1e-8
        assert np.linalg.norm(rotation_matrix(rotations[0].quaternion)-rotation_matrix(expected[6:10])) < 1e-8
        e,p,l = invariants(bodies,rotations)
        assert abs((e-e0)/e0) < 1e-8
        assert l.distance_to(l0)/l0.magnitude() < 1e-8
        assert p.distance_to(p0)/(1e15*2.55) < 1e-12


def test_zero_spin_and_analytic_spherical_free_body():
    state = model(); s = state.rotations[0]
    sphere = replace(s.figure,moments=(2e20,)*3)
    free = replace(s,figure=sphere)
    samples = integrate(state.bodies[:1],(free,),[0.,10.,100.])
    r0 = rotation_matrix(free.quaternion); omega = np.array(free.angular_momentum)/2e20
    for t,(_,rotations) in zip([0,10,100],samples):
        expected = Rotation.from_rotvec(omega*t).as_matrix()@r0
        assert np.linalg.norm(rotation_matrix(rotations[0].quaternion)-expected) < 1e-9
    stopped = replace(free,angular_momentum=(0.,0.,0.))
    final = integrate(state.bodies[:1],(stopped,),[0.,100.])[-1]
    assert final[1] == (stopped,)


def test_rotation_block_error_is_not_diluted_by_inactive_orbits():
    norms=[]
    for count in (1,100):
        y=np.zeros(6*count+7);y[6*count]=1
        solver=RotationDOP853(lambda t,y:np.zeros_like(y),0.,y,1.,body_count=count)
        k=np.zeros((len(solver.E5),len(y))); k[0,6*count+2]=1.;k[0,-1]=2.
        norms.append(solver._estimate_error_norm(k,.2,np.ones_like(y)))
    assert norms[0]>0 and norms[0]==norms[1]


@pytest.mark.parametrize("backend",["python","rust"])
def test_checkpoint_restart_reset_cli_and_rotation_convergence(tmp_path,capsys,backend):
    if backend=="rust":pytest.importorskip("solar_native")
    state=model();state=replace(state,settings=replace(state.settings,backend=backend))
    half=advance(state,20);path=tmp_path/"with spin.json";save(half,path)
    resumed=load(path)
    assert to_document(resumed)==to_document(half) and to_document(resumed)["schema_version"]==10
    assert resumed.rotations==half.rotations and reset(resumed).rotations==state.rotations
    full=advance(state,40);continued=advance(resumed,20)
    assert full.bodies[1].position.distance_to(continued.bodies[1].position)/12000 < 1e-8
    assert np.linalg.norm(rotation_matrix(full.rotations[0].quaternion)-rotation_matrix(continued.rotations[0].quaternion)) < 1e-8
    info=report(continued)
    assert "orbital+rigid-spin" in info["conservation_scope"] and not info["orbital_angular_momentum_conserved"]
    assert info["energy_joules"]==invariants(continued.bodies,continued.rotations)[0]
    assert main(["run",str(path),str(tmp_path/"final.json"),"--steps","1"])==0
    capsys.readouterr()
    from solar_simulator.convergence import compare_tolerances
    comparison=compare_tolerances(state,10)
    assert comparison["rotation_comparison"]["body"]=="figure"
    assert len(comparison["rotation_comparison"]["attitude_frobenius"])==2


@pytest.mark.parametrize("change",["mass","q","shape","settings","missing","initial","provenance","spin_atol"])
def test_malformed_rotation_checkpoint_rejected(change):
    doc=to_document(advance(model(),1)); original=deepcopy(doc)
    if change=="mass":doc["rotations"][0]["figure"]["mass"]*=2
    if change=="q":doc["rotations"][0]["quaternion"][0]*=2
    if change=="shape":doc["rotations"][0]["angular_momentum"].append(1)
    if change=="settings":doc["settings"]["physics"]="eih-1pn";doc["model"]="eih-1pn-dop853-dynamic-q2"
    if change=="missing":doc["rotations"]=[]
    if change=="initial":doc["initial_rotations"][0]["figure"]["moments"][0]*=.99
    if change=="provenance":doc["rotations"][0]["provenance"]="changed"
    if change=="spin_atol":doc["rotations"][0]["momentum_atol"]=0
    with pytest.raises(ValueError):from_document(doc)
    assert original!=doc


def test_legacy_schema_and_explicit_unsupported_physics():
    state=model()
    old=create_experiment(state.bodies,state.settings)
    doc=to_document(old)
    assert doc["schema_version"]==9 and "rotations" not in doc
    assert from_document(doc).rotations==()
    for settings in [replace(state.settings,physics="eih-1pn"),replace(state.settings,error_control="global-rms"),
                     Settings(50.,integrator="verlet")]:
        with pytest.raises(ValueError):create_experiment(state.bodies,settings,rotations=state.rotations)


def test_pinned_lunar_cli_initialization_and_no_future_orientation(tmp_path,monkeypatch):
    import solar_simulator.orientation as orientation
    monkeypatch.setattr(orientation,"lunar_rotation",lambda *a:(_ for _ in ()).throw(AssertionError("future orientation")))
    path=tmp_path/"lunar.json"
    assert main(["new","solar-system-moon",str(path),"--rotation","lunar-solid","--relative-pair","Earth","Moon"])==0
    state=load(path)
    assert len(state.rotations)==1 and state.rotations[0].body=="Moon"
    assert advance(state,1).time>0
    bodies,origin=solar_system(resolved_moon=True)
    bodies[3]=replace(bodies[3],position=bodies[3].position.add(Vector3(1,0,0)))
    with pytest.raises(ValueError):lunar_initial(bodies,origin)
