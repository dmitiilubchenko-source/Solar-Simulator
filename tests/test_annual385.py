"""Small arithmetic/fault tests, not annual integrations or qualification."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil

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


EVIDENCE=Path(__file__).resolve().parents[1]/'scripts/validation/annual385'
MANIFEST_SHA='8c3662cbce2735993a804d40457411f4f9502f657d09b99bf7f36ec0501c1912'


def evidence(directory=EVIDENCE):
    if digest(directory/'manifest.json')!=MANIFEST_SHA:
        raise ValueError('Changed frozen evidence manifest')
    manifest=json.loads((directory/'manifest.json').read_bytes())
    for name,expected in manifest['assets'].items():
        if digest(directory/name)!=expected:
            raise ValueError('Changed evidence asset: '+name)
    return manifest,json.loads((directory/'assessment.json').read_bytes())


def test_all_saved_annual_metrics_replay_without_native_or_integration():
    manifest,report=evidence()
    names=manifest['names'];e,m=names.index('Earth'),names.index('Moon')
    frames=0
    with np.load(EVIDENCE/'states.npz',allow_pickle=False) as data:
        for key,job in report['executed_jobs'].items():
            value=data[key+'_values'];frames+=len(value)
            reference=data['reference_'+('holdout' if key.endswith('holdout20') else 'annual')+'_level_1']
            row=report['results'][key]
            for i,name in enumerate(names):
                assert scalar_errors(value[:,i],reference[:,i])==pytest.approx(row['per_body'][name],rel=4e-15,abs=1e-18)
            assert scalar_errors(value[:,m]-value[:,e],reference[:,m]-reference[:,e])==pytest.approx(row['earth_moon'],rel=4e-15,abs=1e-18)
            if not key.endswith('holdout20'):
                for i,name in enumerate(names):
                    expected=row['jpl']['jpl_residuals'][name]
                    observed=scalar_errors(value[:,i],data['jpl_values'][:,i])
                    assert all(observed[k]==pytest.approx(expected[k],rel=4e-15,abs=1e-18) for k in observed)
            if key.endswith('strict20'):
                assert np.array_equal(data[key+'_resumed_values'],value[len(value)//2:])
    assert frames==768
    assert len(report['gates'])==25 and all(report['gates'].values())
    assert not report['results']['rust_standard20']['checks_passed']
    assert report['results']['rust_standard20']['earth_moon']['position_metres']>.1
    assert manifest['compatibility_status']=='UNRESOLVED'
    assert not manifest['complete_release_qualified'] and not manifest['current_runtime_qualified_by_replay']


@pytest.mark.parametrize('target',['manifest.json','environment.json','states.npz','current-receipt.json'])
def test_published_evidence_corruption_is_read_only(tmp_path,target):
    directory=tmp_path/'evidence';shutil.copytree(EVIDENCE,directory)
    path=directory/target;path.write_bytes(path.read_bytes()+b'changed')
    before={p.name:p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(ValueError,match='Changed'):evidence(directory)
    assert {p.name:p.read_bytes() for p in directory.iterdir()}==before
