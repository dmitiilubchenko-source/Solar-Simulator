"""Small arithmetic/fault tests, not annual integrations or qualification."""
from dataclasses import asdict
import hashlib

import numpy as np
import pytest

from scripts.assess_annual385 import scalar_errors, scalar_invariants, validate_archive
from solar_simulator.diagnostics import model_invariants
from solar_simulator.oblateness import FixedJ2
from solar_simulator.relativity import C
from solar_simulator.simulation import Body, G
from solar_simulator.vector3 import Vector3


def test_verification_runs_after_real_driver_activation_and_restores_on_failure():
    from contextlib import contextmanager
    from types import SimpleNamespace
    from scripts.qualify_annual385 import verified_activation
    events=[]
    original=lambda runtime:events.append(('original_guard',runtime))
    driver=SimpleNamespace(activate=original)
    def check():
        assert events==[('original_guard','candidate')]
        events.append('verified')
    @contextmanager
    def observed():
        events.append('observe_enter')
        try:yield
        finally:events.append('observe_exit')
    with pytest.raises(RuntimeError,match='fault'):
        with verified_activation(driver,check,observed):
            driver.activate('candidate')
            raise RuntimeError('fault')
    assert events==[('original_guard','candidate'),'verified','observe_enter','observe_exit']
    assert driver.activate is original


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_independent_reduction_known_geometry():
    a=np.array([[[3.,4.,0.,0.,0.,12.]],[[0.,0.,0.,0.,0.,0.]]])
    assert scalar_errors(a,np.zeros_like(a)) == {'position_metres':5.,'velocity_m_per_s':12.}


def test_scalar_single_body_relativistic_units():
    state=np.array([[1.,2.,3.,10.,0.,0.]])
    E,P,L=scalar_invariants(state,[2.],['x'],[],G,C)
    assert E == pytest.approx(100.+.375*2.*10000./C**2,rel=1e-15)
    assert P == pytest.approx([20.*(1.+50./C**2),0.,0.],rel=1e-15)
    assert L == pytest.approx([0.,3*P[0],-2*P[0]],rel=1e-15)


@pytest.mark.parametrize('with_figure',[False,True])
def test_scalar_invariants_independent_of_vectorized_runtime(with_figure):
    rng=np.random.default_rng(385)
    values=np.column_stack((rng.normal(size=(4,3))*1e10,rng.normal(size=(4,3))*1e4))
    masses=np.array([1e29,1e24,2e24,1e22]);names=['a','b','c','d']
    figures=(FixedJ2('a',.001,1e7,(0.,0.,1.)),) if with_figure else ()
    bodies=[Body(n,float(m),Vector3(*s[:3]),Vector3(*s[3:])) for n,m,s in zip(names,masses,values)]
    actual=scalar_invariants(values,masses,names,[asdict(f) for f in figures],G,C)
    expected=model_invariants(bodies,'eih-1pn',figures)
    assert actual[0] == pytest.approx(expected[0],rel=3e-15)
    assert actual[1] == pytest.approx([expected[1].x,expected[1].y,expected[1].z],rel=3e-15)
    assert actual[2] == pytest.approx([expected[2].x,expected[2].y,expected[2].z],rel=3e-15)


@pytest.mark.parametrize('fault',['sha','missing','shape','nan'])
def test_saved_array_faults_fail_without_writes(tmp_path,fault):
    path=tmp_path/'raw.npz'
    values=np.zeros((2,3,6))
    if fault=='nan':values[0,0,0]=np.nan
    with path.open('xb') as f:np.savez_compressed(f,states=values)
    before=path.read_bytes()
    shapes={'missing':(2,3,6)} if fault=='missing' else {'states':(3,3,6) if fault=='shape' else (2,3,6)}
    with pytest.raises(ValueError,match='SHA|Incomplete|nonfinite'):
        validate_archive(path,'0'*64 if fault=='sha' else digest(path),shapes,digest)
    assert path.read_bytes()==before
    assert len(list(tmp_path.iterdir()))==1


def test_complete_saved_array_has_independent_copy(tmp_path):
    path=tmp_path/'raw.npz';original=np.zeros((2,3,6))
    with path.open('xb') as f:np.savez_compressed(f,states=original)
    out=validate_archive(path,digest(path),{'states':original.shape},digest)
    out['states'][0,0,0]=1.
    with np.load(path,allow_pickle=False) as data:assert data['states'][0,0,0]==0.
