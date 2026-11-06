"""Instrument/summary contracts; no production optimization is installed."""
from pathlib import Path
import hashlib
from types import SimpleNamespace
import pytest
from scripts.q2_r_reuse394 import (verify_sources,capture_rhs,paired_summary,numeric_bytes,PATCH_SHA256)


@pytest.mark.parametrize('value',[True,float('nan'),float('inf'),-1.,0.,'1'])
def test_timing_rejects_invalid_values(value):
    with pytest.raises(ValueError):paired_summary([(1.,value)]*5)


def test_timing_summary_preserves_pairs_and_reports_exact_sign_probability():
    pairs=[(1.,.9)]*5;before=repr(pairs);r=paired_summary(pairs)
    assert r['one_sided_sign_p']==1/32 and r['positive_series']==5
    assert r['speedup']['median']==pytest.approx(1/.9)
    assert r['absolute_saving']['median']==pytest.approx(.1) and repr(pairs)==before
    assert paired_summary([(1.,1.)]*5)['one_sided_sign_p']==1


def test_patch_binding_and_missing_or_tampered_source_are_rejected(tmp_path):
    root=Path(__file__).resolve().parents[1]
    assert hashlib.sha256((root/'scripts/validation/q2-r-reuse394.patch').read_bytes()).hexdigest()==PATCH_SHA256
    with pytest.raises(ValueError):verify_sources(root,'other')
    with pytest.raises(FileNotFoundError):verify_sources(tmp_path,'prototype')
    path=tmp_path/'src/solar_simulator';path.mkdir(parents=True);(path/'rotation.py').write_text('changed')
    with pytest.raises(ValueError,match='SHA'):verify_sources(tmp_path,'prototype')


def test_rhs_capture_uses_existing_initialization_and_restores_hook_on_failure():
    import numpy as np
    from scripts.two_q2_fixture380 import fixture
    from solar_simulator import nbody_rotation as nr
    from solar_simulator.experiment import create_experiment
    b,r,s=fixture();state=create_experiment(b,s,rotations=r);old=nr.solve_ivp
    result=capture_rhs(nr,state)
    assert nr.solve_ivp is old and result['span']==(0.,50.)
    before=result['y0'].tobytes();derivative=result['fun'](0.,result['y0'])
    assert derivative.shape==result['y0'].shape and np.all(np.isfinite(derivative))
    assert result['y0'].tobytes()==before
    broken=SimpleNamespace(solve_ivp=old,integrate=lambda *a,**kw:(_ for _ in ()).throw(ValueError('rejected')))
    with pytest.raises(ValueError,match='rejected'):capture_rhs(broken,state)
    assert broken.solve_ivp is old


def test_numeric_bytes_detects_signed_zero_and_rejects_bool():
    a=dict(positions=[[0.,0.,0.]],velocities=[[0.,0.,0.]],quaternions=[],spins=[])
    b={**a,'positions':[[-0.,0.,0.]]};assert numeric_bytes(a)!=numeric_bytes(b)
    with pytest.raises(ValueError):numeric_bytes({**a,'positions':[[True,0.,0.]]})
    with pytest.raises(ValueError):numeric_bytes({**a,'spins':[[0.,0.]]})
