"""Raw Jacobi persistence, source guards, independent exports and process restart."""
from dataclasses import replace
import hashlib
import json
import subprocess
import sys

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts.canonical_checkpoint import (CanonicalCheckpoint, canonical_text,
    to_document as cartesian_document, from_document as cartesian_from_document, parse_json)
from scripts.relative_canonical_checkpoint import (RelativeCheckpoint,from_cartesian_checkpoint,
    to_document,from_document,save,load,evolve,verify_sources,velocity_export,CORE_SOURCES,RUNNING_ROOT)
from scripts.relative_canonical import Pair,to_cartesian
from scripts.independent_relative_canonical import gradients
from scripts.rigid_pn_model import Parameters
from scripts.nbody_pn_spin import Parameters as PointParameters
from solar_simulator.rotation import RigidFigure


P = Parameters(PointParameters((.3,.7,.05),float(np.sqrt(1e5))),
    RigidFigure(.3,(.002,.0025,.003),.15),0)
Y = np.r_[np.array([[[.56,0.,0.],[-.24,0.,0.],[3.5,.4,.6]],
    [[0.,.257,0.],[0.,-.257,0.],[-.003,.025,.004]],
    [[.003,-.004,.002],[-.002,.001,.003],[.0002,.0003,-.0001]]]).ravel(),[1.,0.,0.,0.]]


def fixture_cartesian():
    meta = dict(frame=dict(name='synthetic fixed frame',centre='canonical-ADM-centres',spin_basis='finite-H-spatial-Euclidean',
        time_coordinate='model-coordinate-time',epoch_jd=None,evolution='fixed-no-reboost'),units=dict(kind='synthetic-G1'),
        integration=dict(method='canonical-per-block-DOP853',rtol=1e-11,atol=[1e-13]*len(Y),max_step=.02),
        provenance=dict(interpretation='synthetic initial state',physical_mapping_certified=False,
            sources=[dict(path=p,sha256=hashlib.sha256((RUNNING_ROOT/p).read_bytes()).hexdigest()) for p in CORE_SOURCES]))
    return CanonicalCheckpoint(P,tuple(Y),tuple(Y),0.,canonical_text(meta))


def fixture_checkpoint():
    old = fixture_cartesian()
    return from_cartesian_checkpoint(old,Pair(P.orbital.masses,0,1),['first','second','third'],integration=old.metadata['integration'])


def rehash(document):
    d = dict(document); d.pop('payload_sha256')
    document['payload_sha256'] = hashlib.sha256(canonical_text(d).encode('utf-8')).hexdigest()
    return document


def test_bitwise_roundtrip_order_pair_initial_raw_q_and_negative_zero(tmp_path):
    cp = fixture_checkpoint();state = np.array(cp.state);state[1] = -0.;state[-4:] *= 1+2e-10
    cp = replace(cp,state=tuple(state),time=.1);path = tmp_path/'relative state with spaces.json'
    save(path,cp);other = load(path)
    assert np.array_equal(np.array(other.state).view(np.uint64),state.view(np.uint64))
    assert np.array_equal(np.array(other.initial).view(np.uint64),np.array(cp.initial).view(np.uint64))
    assert other.pair==cp.pair and other.parameters==cp.parameters and other.body_names==cp.body_names
    assert other.metadata_json==cp.metadata_json and to_document(other)==to_document(cp)
    meta = other.metadata;meta['frame']['name'] = 'changed';assert other.metadata['frame']['name']=='synthetic fixed frame'
    with pytest.raises(FileExistsError):save(path,cp)


def test_no_implicit_cartesian_legacy_velocity_or_export_migration():
    old = fixture_cartesian();cp = fixture_checkpoint()
    for value in [cartesian_document(old),dict(schema=9,bodies=[]),dict(schema=10,bodies=[],rotations=[]),velocity_export(cp)]:
        with pytest.raises(ValueError):from_document(value)
    with pytest.raises(ValueError):cartesian_from_document(to_document(cp))
    with pytest.raises(ValueError):to_document(old)
    with pytest.raises(ValueError):from_cartesian_checkpoint(old,cp.pair,'abc',integration=old.metadata['integration'])


def test_representation_payload_parameters_names_and_metadata_guards():
    cp = fixture_checkpoint();d = to_document(cp);d['state']['coordinate_slots'][1][0]+=1e-6
    with pytest.raises(ValueError,match='SHA256'):from_document(d)
    mutations = [lambda d:d.update(schema=True),lambda d:d['representation'].update(kind='cartesian-x-p'),
        lambda d:d['representation'].update(pair_indices=[0,0]),lambda d:d['representation'].update(pair_indices=[True,1]),
        lambda d:d.update(body_names=['first','first','third']),lambda d:d['parameters']['figure'].update(mass=True),
        lambda d:d['metadata']['frame'].update(centre='harmonic'),lambda d:d['metadata']['frame'].update(evolution='reboost'),
        lambda d:d['metadata']['provenance'].update(physical_mapping_certified=True),
        lambda d:d['metadata']['integration'].update(atol=[0.]*len(Y)),lambda d:d.update(elapsed_model_time=-1.),
        lambda d:d['state']['spatial_spins'][0].__setitem__(0,'0.003'),lambda d:d['state']['quaternion'].__setitem__(0,True),
        lambda d:d['initial']['quaternion'].__setitem__(0,1.01),lambda d:d['state']['coordinate_slots'][0].__setitem__(0,.1),
        lambda d:d['state'].update(positions=d['state']['coordinate_slots'])]
    for mutate in mutations:
        d = to_document(cp);mutate(d)
        with pytest.raises(ValueError):from_document(rehash(d))


def test_geometry_validation_keeps_sub_ulp_relative_vector(tmp_path):
    cp = fixture_checkpoint();params = Parameters(PointParameters((.3,.7),1e6),P.figure,0);pair = Pair((.3,.7),0,1)
    raw = np.r_[np.array([[[2.**54]*3,[.25,.5,1.]],[[0.,.01,0.],[0.,.02,0.]],[[.003,0.,0.],[0.,0.,0.]]]).ravel(),[1.,0.,0.,0.]]
    meta = cp.metadata;meta['integration']['atol'] = [1e-13]*len(raw)
    relative = RelativeCheckpoint(params,pair,('first','second'),tuple(raw),tuple(raw),0.,canonical_text(meta))
    path = tmp_path/'huge origin.json';save(path,relative);other = load(path)
    assert np.array_equal(np.array(other.state).view(np.uint64),raw.view(np.uint64))
    assert np.array_equal(to_cartesian(other.state,pair,anchored=True)[3:6],raw[3:6])


def test_nonfinite_duplicate_keys_and_signed_zero_t0_rejection():
    for value in ['{"a":1,"a":2}','{"x":NaN}','{"x":Infinity}']:
        with pytest.raises(ValueError):parse_json(value)
    cp = fixture_checkpoint();current = np.array(cp.state);current[1] = -0.
    with pytest.raises(ValueError,match='bitwise'):replace(cp,state=tuple(current))
    for value in [float('nan'),float('inf')]:
        current = np.array(cp.state);current[0] = value
        with pytest.raises(ValueError):replace(cp,state=tuple(current),time=.1)


def test_independent_canonical_velocity_exports_and_SI_scaling():
    cp = fixture_checkpoint();rotation = Rotation.from_quat(np.roll(cp.state[-4:],-1)).as_matrix()
    g = gradients(np.array(cp.state[:-4]),rotation,P.orbital.masses,P.orbital.c,P.figure.moments,0,0,1).reshape(3,3,3)
    out = velocity_export(cp);a,d = cp.pair.fractions;expected = g[1].copy()
    expected[0] = g[1,0]-d*g[1,1];expected[1] = g[1,0]+a*g[1,1]
    assert np.max(abs(np.array(out['velocity_model_units'])-expected)) < 1e-14
    assert np.linalg.norm(np.array(out['relative_velocity_model_units'])-g[1,1]) < 1e-14
    assert np.linalg.norm(np.array(out['attitude_rate_model_units'])-g[2,0]) < 1e-14
    meta = cp.metadata;meta['units'] = dict(kind='SI-similarity',mass_kg=1.,length_m=4.,gravitational_constant=1.)
    si = velocity_export(replace(cp,metadata_json=canonical_text(meta)))
    assert np.array_equal(np.array(si['velocity_m_s']),np.array(out['velocity_model_units'])*.5)
    assert np.array_equal(np.array(si['relative_velocity_m_s']),np.array(out['relative_velocity_model_units'])*.5)
    assert np.array_equal(np.array(si['attitude_rate_per_s']),np.array(out['attitude_rate_model_units'])/8.)


def test_verified_process_file_restart_without_frame_or_state_projection(tmp_path):
    cp = fixture_checkpoint();grid = np.linspace(0.,.3,17);end,full = evolve(cp,grid,source_root=RUNNING_ROOT)
    middle,first = evolve(cp,grid[:9],source_root=RUNNING_ROOT);save(tmp_path/'middle.json',middle)
    program = '''
import sys,numpy as np
from scripts.relative_canonical_checkpoint import load,save,evolve,RUNNING_ROOT
cp=load(sys.argv[1]);end,states=evolve(cp,np.linspace(.15,.3,9),source_root=RUNNING_ROOT)
save(sys.argv[2],end);np.savez(sys.argv[3],states=states)
'''
    subprocess.run([sys.executable,'-X','utf8','-B','-c',program,str(tmp_path/'middle.json'),str(tmp_path/'final.json'),str(tmp_path/'suffix.npz')],
        cwd=RUNNING_ROOT,check=True,capture_output=True,text=True)
    last = np.load(tmp_path/'suffix.npz')['states'];joined = np.vstack([first[:-1],last]);restored = load(tmp_path/'final.json')
    assert np.max(abs(full-joined)) < 1e-10
    assert restored.metadata_json==cp.metadata_json and restored.initial==cp.initial and restored.pair==cp.pair
    assert np.array_equal(last[0].view(np.uint64),first[-1].view(np.uint64))
    assert np.array_equal(np.array(restored.state).view(np.uint64),last[-1].view(np.uint64))


def test_source_tree_controls_grid_and_conversion_rejections(tmp_path):
    cp = fixture_checkpoint();verify_sources(cp,RUNNING_ROOT)
    for grid in [[.01,.04],[0.,0.],[0.,float('nan')],[0.,True],0.]:
        with pytest.raises(ValueError):evolve(cp,grid,source_root=RUNNING_ROOT)
    with pytest.raises(ValueError,match='running modules'):evolve(cp,[0.,.04],source_root=tmp_path)
    meta = cp.metadata;meta['provenance']['sources'][0]['sha256'] = '0'*64
    changed = replace(cp,metadata_json=canonical_text(meta))
    with pytest.raises(ValueError,match='source versions'):evolve(changed,[0.,.04],source_root=RUNNING_ROOT)
    with pytest.raises(ValueError,match='SHA256'):verify_sources(changed,RUNNING_ROOT)
    meta = cp.metadata;meta['provenance']['sources'].append(dict(path='../private.json',sha256='b'*64))
    with pytest.raises(ValueError,match='outside-root'):verify_sources(replace(cp,metadata_json=canonical_text(meta)),RUNNING_ROOT)
    old = fixture_cartesian()
    with pytest.raises(ValueError,match='masses'):from_cartesian_checkpoint(old,Pair((.4,.6,.05),0,1),['a','b','c'],integration=old.metadata['integration'])
