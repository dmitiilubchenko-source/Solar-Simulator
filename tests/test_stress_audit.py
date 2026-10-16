import json
import shutil
import subprocess
import sys

import pytest

from scripts import assess_continuum_stress as audit


def policy():
    return json.loads((audit.ROOT/audit.POLICY).read_text(encoding='utf-8'))


@pytest.mark.parametrize('category',['maximum','minimum','required_true'])
def test_each_predeclared_stress_and_cancellation_criterion_is_enforced(category):
    p=policy();metrics={**{k:v/2 for k,v in p['maximum'].items()},**{k:v*2 for k,v in p['minimum'].items()}}
    flags={k:True for k in p['required_true']}
    assert audit.failures(metrics,flags,p)==[]
    for key in p[category]:
        m,f=metrics.copy(),flags.copy()
        if category=='required_true':f[key]=False
        else:m[key]=p[category][key]
        assert audit.failures(m,f,p)==[key]


def test_primary_and_executed_code_changes_rejected(tmp_path,monkeypatch):
    p=policy();name=next(iter(p['primary_sha256']));target=tmp_path/name
    target.parent.mkdir(parents=True);target.write_bytes(b'corrupted')
    for name in audit.USED_POLICIES:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'original')
    monkeypatch.setattr(audit,'ROOT',tmp_path);monkeypatch.setattr(audit,'LOADED_SOURCES',audit.source_hashes())
    audit.check_sources()
    with pytest.raises(ValueError,match='Pinned primary'):audit.primary_hashes(p)
    (tmp_path/audit.POLICY).write_bytes(b'changed')
    with pytest.raises(ValueError,match='sources changed'):audit.check_sources()


def test_scientific_outputs_are_fresh_and_inside_project(tmp_path,monkeypatch):
    hashes=audit.source_hashes()
    for name in ('scripts/continuum_stress.py','scripts/independent_stress_reference.py','scripts/fluid_spin.py',*audit.USED_POLICIES):
        assert name in hashes
    root=tmp_path/'root';root.mkdir();old=root/'report.json';old.write_bytes(b'keep')
    monkeypatch.setattr(audit,'ROOT',root)
    def forbidden():raise AssertionError('Check output paths before jobs or source reads')
    monkeypatch.setattr(audit,'check_sources',forbidden)
    with pytest.raises(FileExistsError):audit.audit(work=root/'fresh',output=old)
    with pytest.raises(ValueError):audit.audit(work=tmp_path/'outside',output=root/'new.json')
    assert old.read_bytes()==b'keep' and not (root/'fresh').exists()


def test_clean_offline_import_does_not_require_private_primary_cache(tmp_path):
    root=tmp_path/'clean';root.mkdir()
    for name in audit.source_hashes():
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(audit.ROOT/name,target)
    code="""from scripts import assess_continuum_stress as a
try:
    a.audit(work=a.ROOT/'fresh',output=a.ROOT/'report.json')
except FileNotFoundError as error:
    assert 'Primary scientific artifact unavailable' in str(error)
    assert not (a.ROOT/'fresh').exists() and not (a.ROOT/'report.json').exists()
else:
    raise AssertionError('Fresh audit must reject missing primary artifacts')
"""
    result=subprocess.run([sys.executable,'-X','utf8','-B','-c',code],cwd=root,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
