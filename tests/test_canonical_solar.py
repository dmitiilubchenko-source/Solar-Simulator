"""Ten-body immutable initial data and non-diluted internal orbit comparison."""
import json

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

from scripts.assess_canonical_solar import initial_checkpoint, differences, ROOT
from scripts.canonical_checkpoint import load, verify_sources
from scripts.independent_rigid_pn import gradients


def policy():return json.loads((ROOT/'scripts/canonical-solar-policy.json').read_text(encoding='utf-8'))


def test_ten_body_state_bitwise_and_independent_initial_kinematics():
    cp,units,names=initial_checkpoint(policy());old=load(ROOT/policy()['input_checkpoint'])
    assert np.array_equal(np.array(cp.state).view(np.uint64),np.array(old.state).view(np.uint64))
    verify_sources(cp,ROOT);p=cp.parameters;b=np.array(cp.state[:-4]).reshape(3,10,3)
    r=Rotation.from_quat(np.roll(cp.state[-4:],-1)).as_matrix()
    g,_=gradients(b.ravel(),r,p.orbital.masses,p.orbital.c,p.figure.moments,p.index)
    expected=np.array([b['velocity'] for b in json.loads((ROOT/'src/solar_simulator/data/solar-system-moon-20261008.json').read_text(encoding='utf-8'))['bodies']])
    v=g.reshape(3,10,3)[1]*units.velocity_m_s
    assert np.max(np.linalg.norm(v-expected,axis=1)/np.linalg.norm(expected,axis=1))<1e-12
    assert cp.metadata['provenance']['physical_mapping_certified'] is False


def test_ten_body_relative_error_is_separate_from_absolute_planet_error():
    cp,units,names=initial_checkpoint(policy());a=np.array([cp.state[:-4]]);b=a.copy()
    r=Rotation.from_quat(np.roll(cp.state[-4:],-1)).as_matrix()[None];e=names.index('Earth');f=names.index('Moon')
    spin=np.linalg.norm(a.reshape(1,3,10,3)[0,2,f]);b.reshape(1,3,10,3)[0,0,e,0]+=100/units.length_m
    b.reshape(1,3,10,3)[0,0,f,0]-=100/units.length_m
    result=differences(a,r,b,r,units,10,e,f,spin)
    assert 99.99<result['positions_m']<100.01 and 199.99<result['earth_moon_position_m']<200.01
    assert len(result['positions_per_body_m'])==10


def test_immutable_input_and_body_scope_rejections():
    for key,value in [('input_checkpoint_sha256','0'*64),('physical_lunar_mapping_certified',True),
                      ('body_names',['Sun','Earth','Moon'])]:
        with pytest.raises(ValueError):initial_checkpoint(dict(policy(),**{key:value}))
