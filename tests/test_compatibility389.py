"""Guard/provenance contracts; no scientific integrations."""
from types import SimpleNamespace
import pytest
from scripts.check_compatibility389 import install_profile,canonical_sha,SelfGuard,read


def test_shared_profile_preserves_controls(monkeypatch):
    import os
    keys=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS','NUMEXPR_NUM_THREADS','PYTHONHASHSEED')
    for key in keys:monkeypatch.setenv(key,'99')
    install_profile()
    assert [os.environ.get(k) for k in keys]==['1','1','1',None,None,None]


def test_canonical_fingerprint_order_and_finite_values():
    assert canonical_sha(dict(a=1,b=2))==canonical_sha(dict(b=2,a=1))
    with pytest.raises(ValueError):canonical_sha(dict(a=float('nan')))


def test_self_guard_keeps_completed_peak(tmp_path):
    samples=iter([dict(PrivateUsage=400),dict(PrivateUsage=200)])
    guard=SelfGuard(SimpleNamespace(windows_memory=lambda:next(samples)),tmp_path)
    guard.sample();guard.sample()
    assert guard.peak==400 and guard.samples==2


def test_self_guard_persists_stop_without_weakening_limit(tmp_path,monkeypatch):
    from scripts import check_compatibility389 as tool
    def stop(code):raise SystemExit(code)
    monkeypatch.setattr(tool.os,'_exit',stop)
    guard=SelfGuard(SimpleNamespace(windows_memory=lambda:dict(PrivateUsage=900*1024**2+1)),tmp_path)
    with pytest.raises(SystemExit) as error:guard.sample()
    assert error.value.code==90 and read(tmp_path/'self-stop.json')['reason']=='private-memory'
