import json
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
import pytest

from scripts import assess_fluid_spin as audit
from scripts import fluid_spin as spin
from scripts import independent_fluid_reference as reference


def policy():return json.loads((audit.ROOT/audit.POLICY).read_text(encoding='utf-8'))


def test_Riccati_boundary_conversion_and_matter_integral_Newton_limit():
    raw=np.array([1.8,.9]);c=.2;z=raw[1]/raw[0]
    assert abs(reference.riccati_inertia(z,c)-spin.boundary(raw,c)['inertia_factor'])<1e-11
    s,w=np.polynomial.legendre.leggauss(32);s=(s+1)/2;w=w/2
    integral=np.dot(w,reference.inertia_integrand(s,1e-12,np.ones_like(s)))
    assert abs(integral-.4)<1e-11


def test_inward_TOV_independent_analytic_pressure_derivative():
    for s,c in ((0.,.25),(.2,.25),(.8,.25),(1.,.25)):
        derivative=reference.pressure(s+1j*1e-20,c).imag/1e-20
        flow=reference.tov_rhs(s,[reference.pressure(s,c)],c)[0]
        assert abs(derivative-flow)<1e-11


@pytest.mark.parametrize('category',['maximum','minimum','required_true'])
def test_each_fixed_audit_criterion_is_enforced(category):
    p=policy();metrics={**{k:v/2 for k,v in p['maximum'].items()},**{k:v*2 for k,v in p['minimum'].items()}}
    flags={k:True for k in p['required_true']}
    assert audit.failures(metrics,flags,p)==[]
    for key in p[category]:
        m,f=metrics.copy(),flags.copy()
        if category=='required_true':f[key]=False
        else:m[key]=p[category][key]
        assert audit.failures(m,f,p)==[key]


def test_source_closure_and_primary_artifact_guard(tmp_path,monkeypatch):
    hashes=audit.source_hashes()
    for name in ('scripts/continuum_sphere.py','scripts/fluid_spin.py','scripts/independent_fluid_reference.py','scripts/assess_metric_spin.py',*audit.USED_POLICIES):assert name in hashes
    assert all(name not in hashes for name in audit.PRIMARY_ARTIFACTS)
    for name in (*audit.USED_POLICIES,*audit.PRIMARY_ARTIFACTS):
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'original')
    monkeypatch.setattr(audit,'ROOT',tmp_path);monkeypatch.setattr(audit,'LOADED_SOURCES',audit.source_hashes())
    audit.check_sources();primary=audit.primary_hashes()
    (tmp_path/audit.PRIMARY_ARTIFACTS[0]).write_bytes(b'changed')
    audit.check_sources()
    with pytest.raises(ValueError,match='changed'):audit.check_primary_sources(primary)


def test_existing_or_outside_output_rejected_before_scientific_jobs(tmp_path,monkeypatch):
    root=tmp_path/'root';root.mkdir();monkeypatch.setattr(audit,'ROOT',root)
    def forbidden():raise AssertionError('No source reads or jobs allowed')
    monkeypatch.setattr(audit,'check_sources',forbidden)
    old=root/'report.json';old.write_bytes(b'preserved')
    with pytest.raises(FileExistsError):audit.audit(work=root/'new',output=old)
    with pytest.raises(ValueError):audit.audit(work=tmp_path/'outside',output=root/'new.json')
    assert old.read_bytes()==b'preserved' and not (root/'new').exists()


def test_clean_source_import_without_private_cache_and_audit_missing_primary_rejected(tmp_path):
    # Reproduce the actual offline import in a child interpreter, not sys.modules cache.
    root=tmp_path/'clean';root.mkdir()
    for name in audit.source_hashes():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(audit.ROOT/name,path)
    script="""from scripts import assess_fluid_spin as a
try:
    a.audit(work=a.ROOT/'fresh', output=a.ROOT/'report.json')
except FileNotFoundError as error:
    assert 'Primary scientific artifact unavailable' in str(error)
    assert not (a.ROOT/'fresh').exists()
    assert not (a.ROOT/'report.json').exists()
else:
    raise AssertionError('Missing primary artifacts must reject fresh scientific audit')
"""
    result=subprocess.run([sys.executable,'-X','utf8','-B','-c',script],cwd=root,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
