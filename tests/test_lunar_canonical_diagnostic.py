"""Pinned conditional input, independent kinematics and relative-orbit scales."""
from dataclasses import replace
import json

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts.lunar_canonical_diagnostic import initial_checkpoint, differences, ROOT
from scripts.canonical_checkpoint import to_document, from_document, velocity_export
from scripts.independent_rigid_pn import gradients


def policy():
    return json.loads((ROOT/'scripts/lunar-canonical-policy.json').read_text(encoding='utf-8'))


def test_conditional_lunar_initial_matches_independent_H_derivatives():
    cp, units, info = initial_checkpoint(policy()); p = cp.parameters
    b = np.array(cp.state[:-4]).reshape(3,3,3)
    r = Rotation.from_quat(np.roll(cp.state[-4:],-1)).as_matrix()
    g,_ = gradients(b.ravel(),r,p.orbital.masses,p.orbital.c,p.figure.moments,2);g=g.reshape(b.shape)
    v = g[1]*units.velocity_m_s; w=g[2,2]/units.time_s
    expected=np.array(info['input_velocity_m_s']); expected_w=np.array(info['input_attitude_rate_per_s'])
    assert np.max(np.linalg.norm(v-expected,axis=1)/np.linalg.norm(expected,axis=1))<1e-12
    assert np.linalg.norm(w-expected_w)/np.linalg.norm(expected_w)<1e-12
    assert np.array_equal(b[2,:2],np.zeros((2,3)))
    assert cp.metadata['provenance']['physical_mapping_certified'] is False
    assert info['parent_file_body_count']==10 and info['selected_body_count']==3
    restored=from_document(to_document(cp))
    assert np.array_equal(np.array(restored.state).view(np.uint64),np.array(cp.state).view(np.uint64))
    assert velocity_export(restored)['definition']=='dx_canonical/dt; not harmonic velocity'


def test_dataset_or_frame_changes_and_false_physical_certification_rejected():
    for key,value in [('orbital_data_sha256','0'*64),('spin_profile_sha256','0'*64),
                      ('frame','ICRF'),('epoch_jd_tdb',2461322.5),
                      ('body_names',['Earth','Moon','Sun']),('physical_lunar_mapping_certified',True)]:
        with pytest.raises(ValueError):
            initial_checkpoint(dict(policy(),**{key:value}))


def test_relative_earth_moon_error_not_hidden_by_common_translation():
    cp,units,_=initial_checkpoint(policy());a=np.array([cp.state[:-4]]);b=a.copy()
    r=Rotation.from_quat(np.roll(cp.state[-4:],-1)).as_matrix()[None]
    spin=np.linalg.norm(a.reshape(1,3,3,3)[0,2,2])
    # A common 100 m translation has no relative Earth-Moon change.
    b.reshape(1,3,3,3)[:,0,:,0]+=100/units.length_m
    result=differences(a,r,b,r,units,spin)
    assert 99.99<result['positions_m']<100.01 and result['earth_moon_position_m']<1e-4
    # Opposite offsets can double the internal-orbit error.
    b=a.copy();b.reshape(1,3,3,3)[0,0,1,0]+=100/units.length_m
    b.reshape(1,3,3,3)[0,0,2,0]-=100/units.length_m
    result=differences(a,r,b,r,units,spin)
    assert 199.99<result['earth_moon_position_m']<200.01
    with pytest.raises(ValueError):
        differences(a,r,b[:,:26],r,units,spin)
