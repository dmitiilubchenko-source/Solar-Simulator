"""A pinned conditional input cannot silently become a physical PN migration."""
from scripts.release_history import verify_checkpoint_history
from dataclasses import replace
import hashlib
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

import scripts.lunar_initial_boundary as boundary
import solar_simulator.spin_initial as profile_module
from scripts.canonical_initial import SIUnits,kinematics,from_velocities_and_rate
from scripts.relative_canonical_checkpoint import load,verify_sources
from scripts.relative_canonical import to_cartesian
from scripts.independent_rigid_pn import gradients
from solar_simulator.rotation import RigidFigure


ROOT = Path(__file__).resolve().parents[1]
INPUT_SHA = '02ee4efa985402898568d13e41050bfad6da5717e0148ab08a3f6a4e1af20623'


@pytest.fixture
def inputs():
    path = ROOT/'.tools/rotation63/initial.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest()==INPUT_SHA
    cp = load(path);verify_checkpoint_history(cp,ROOT)
    units = SIUnits(**{k:v for k,v in cp.metadata['units'].items() if k!='kind'})
    y = to_cartesian(cp.initial,cp.pair);v,w = kinematics(y,cp.parameters)
    return dict(positions=y[:30].reshape(10,3),velocities=v,parameters=cp.parameters,
        units=units,body_names=cp.body_names,purpose=boundary.PURPOSE,epoch_jd_tdb=2461321.5,
        frame='Ecliptic J2000',velocity_scales=np.linalg.norm(v,axis=1),rate_scale=np.linalg.norm(w))


def test_conditional_result_matches_old_inversion_bitwise_and_independent_H(inputs):
    args = inputs;state,info = boundary.from_lunar_profile(**args)
    _,_,pair,profile = profile_module.lunar_solid_equivalent_initial()
    r = np.array(profile['rotation']);h = np.array(profile['rotation_derivative_per_second'])@r.T
    h = .5*(h-h.T);w = np.array([h[2,1],h[0,2],h[1,0]])*args['units'].time_s
    count = len(args['body_names']);p = args['parameters']
    old,_ = from_velocities_and_rate(args['positions'],args['velocities'],pair[6:10],w,
        np.zeros((count,3)),p,velocity_scales=args['velocity_scales'],rate_scale=args['rate_scale'])
    assert np.array_equal(state.view(np.uint64),old.view(np.uint64))
    rotation = Rotation.from_quat(np.roll(state[-4:],-1)).as_matrix()
    g,_ = gradients(state[:-4],rotation,p.orbital.masses,p.orbital.c,p.figure.moments,p.index)
    g = g.reshape(3,count,3)
    assert np.max(np.linalg.norm(g[1]-args['velocities'],axis=1)/args['velocity_scales'])<1e-13
    assert np.linalg.norm(g[2,p.index]-w)/args['rate_scale']<1e-13
    contract = info['boundary_contract']
    assert contract['physical_mapping_certified'] is False
    assert contract['inertia_radius_time_compatibility']=='unqualified'
    assert contract['clock_basis_SSC_transform']=='not applied'
    assert contract['source_profile_sha256']==profile_module.PROFILE_SHA256


@pytest.mark.parametrize('purpose',['physical-lunar','physical-certified','local-clock',True,None])
def test_physical_or_implicit_purpose_rejected_before_profile_or_inversion(inputs,monkeypatch,purpose):
    def forbidden(*args,**kwargs):pytest.fail('Rejected request reached profile/inversion')
    monkeypatch.setattr(boundary,'lunar_solid_equivalent_initial',forbidden)
    monkeypatch.setattr(boundary,'from_velocities_and_rate',forbidden)
    with pytest.raises(ValueError,match='not certified'):boundary.from_lunar_profile(**dict(inputs,purpose=purpose))


@pytest.mark.parametrize('kind',['epoch','frame','units','names','mass','inertia','radius','c'])
def test_changed_profile_conventions_or_parameters_rejected_before_inversion(inputs,monkeypatch,kind):
    args = dict(inputs);p = args['parameters'];u = args['units']
    if kind=='epoch':args['epoch_jd_tdb']+=1
    elif kind=='frame':args['frame']='ICRF'
    elif kind=='units':args['units']=replace(u,gravitational_constant=u.gravitational_constant*1.001)
    elif kind=='names':args['body_names']=tuple('Earth' if n=='Moon' else n for n in args['body_names'])
    elif kind=='mass':args['units']=replace(u,mass_kg=u.mass_kg*1.001)
    elif kind=='inertia':args['parameters']=replace(p,figure=RigidFigure(p.figure.mass,tuple(v*.99 for v in p.figure.moments),p.figure.bounding_radius))
    elif kind=='radius':args['parameters']=replace(p,figure=replace(p.figure,bounding_radius=p.figure.bounding_radius*1.01))
    else:args['parameters']=replace(p,orbital=replace(p.orbital,c=p.orbital.c*1.01))
    def forbidden(*args,**kwargs):pytest.fail('Mismatched conventions reached inversion')
    monkeypatch.setattr(boundary,'from_velocities_and_rate',forbidden)
    with pytest.raises(ValueError):boundary.from_lunar_profile(**args)


def test_corrupted_source_and_missing_explicit_purpose_are_rejected(inputs,monkeypatch):
    monkeypatch.setattr(profile_module,'PROFILE_SHA256','0'*64)
    with pytest.raises(ValueError,match='профиль'):boundary.from_lunar_profile(**inputs)
    args = dict(inputs);args.pop('purpose')
    with pytest.raises(TypeError):boundary.from_lunar_profile(**args)
