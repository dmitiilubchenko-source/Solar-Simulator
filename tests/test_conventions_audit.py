import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts import assess_continuum_conventions as audit


def policy():
    return json.loads((audit.ROOT/audit.POLICY).read_text(encoding='utf-8'))


@pytest.mark.parametrize('category',['maximum','minimum','required_true'])
def test_every_predeclared_convention_criterion_is_enforced(category):
    p=policy();metrics={**{k:v/2 for k,v in p['maximum'].items()},**{k:v*2 for k,v in p['minimum'].items()}}
    flags={k:True for k in p['required_true']}
    assert audit.failures(metrics,flags,p)==[]
    for key in p[category]:
        m,f=metrics.copy(),flags.copy()
        if category=='required_true':f[key]=False
        else:m[key]=p[category][key]
        assert audit.failures(m,f,p)==[key]


def test_primary_SHA_rejects_existing_corrupted_cache(tmp_path,monkeypatch):
    p=policy();name=next(iter(p['primary_sha256']));target=tmp_path/name
    target.parent.mkdir(parents=True);target.write_bytes(b'corrupted')
    monkeypatch.setattr(audit,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='Pinned primary'):audit.primary_hashes(p)


def test_fresh_outputs_and_source_closure_guards(tmp_path,monkeypatch):
    hashes=audit.source_hashes()
    for name in ('scripts/continuum_conventions.py','scripts/independent_conventions_reference.py','scripts/fluid_spin.py',*audit.USED_POLICIES):
        assert name in hashes
    assert all(name not in hashes for name in policy()['primary_sha256'])
    root=tmp_path/'root';root.mkdir();old=root/'report.json';old.write_bytes(b'keep')
    monkeypatch.setattr(audit,'ROOT',root)
    def forbidden():raise AssertionError('Outputs checked before sources/jobs')
    monkeypatch.setattr(audit,'check_sources',forbidden)
    with pytest.raises(FileExistsError):audit.audit(work=root/'fresh',output=old)
    with pytest.raises(ValueError):audit.audit(work=tmp_path/'outside',output=root/'fresh.json')
    assert old.read_bytes()==b'keep' and not (root/'fresh').exists()


def test_offline_source_import_and_explicit_missing_primary_before_jobs(tmp_path):
    root=tmp_path/'clean';root.mkdir()
    for name in audit.source_hashes():
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(audit.ROOT/name,target)
    code="""from scripts import assess_continuum_conventions as a
try:
    a.audit(work=a.ROOT/'fresh',output=a.ROOT/'report.json')
except FileNotFoundError as error:
    assert 'Primary scientific artifact unavailable' in str(error)
    assert not (a.ROOT/'fresh').exists() and not (a.ROOT/'report.json').exists()
else:
    raise AssertionError('Fresh scientific audit requires verified primary artifacts')
"""
    result=subprocess.run([sys.executable,'-X','utf8','-B','-c',code],cwd=root,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
