import json
import shutil
import subprocess
import sys

import pytest

from scripts import assess_harmonic_sphere as audit


def policy():return json.loads((audit.ROOT/audit.POLICY).read_text(encoding='utf-8'))


@pytest.mark.parametrize('category',['maximum','minimum','required_true'])
def test_all_harmonic_chart_criteria_are_enforced(category):
    p=policy();m={**{k:v/2 for k,v in p['maximum'].items()},**{k:v*2 for k,v in p['minimum'].items()}};f={k:True for k in p['required_true']}
    assert audit.failures(m,f,p)==[]
    for key in p[category]:
        mm,ff=m.copy(),f.copy()
        if category=='required_true':ff[key]=False
        else:mm[key]=p[category][key]
        assert audit.failures(mm,ff,p)==[key]


def test_primary_corruption_and_code_changes_rejected(tmp_path,monkeypatch):
    p=policy();name=next(iter(p['primary_sha256']));path=tmp_path/name;path.parent.mkdir(parents=True);path.write_bytes(b'corrupted')
    for name in audit.USED_POLICIES:
        path=tmp_path/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'original')
    monkeypatch.setattr(audit,'ROOT',tmp_path);monkeypatch.setattr(audit,'LOADED_SOURCES',audit.source_hashes())
    audit.check_sources()
    with pytest.raises(ValueError,match='Pinned primary'):audit.primary_hashes(p)
    (tmp_path/audit.POLICY).write_bytes(b'changed')
    with pytest.raises(ValueError,match='sources changed'):audit.check_sources()


def test_fresh_output_paths_checked_before_jobs(tmp_path,monkeypatch):
    root=tmp_path/'root';root.mkdir();old=root/'old.json';old.write_bytes(b'keep');monkeypatch.setattr(audit,'ROOT',root)
    def forbidden():raise AssertionError('Check paths before source reads')
    monkeypatch.setattr(audit,'check_sources',forbidden)
    with pytest.raises(FileExistsError):audit.audit(work=root/'fresh',output=old)
    with pytest.raises(ValueError):audit.audit(work=tmp_path/'outside',output=root/'new.json')
    assert old.read_bytes()==b'keep' and not (root/'fresh').exists()


def test_offline_import_and_missing_primary_reject_before_jobs(tmp_path):
    root=tmp_path/'clean';root.mkdir()
    for name in audit.source_hashes():
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(audit.ROOT/name,target)
    code="""from scripts import assess_harmonic_sphere as a
try:
 a.audit(work=a.ROOT/'fresh',output=a.ROOT/'report.json')
except FileNotFoundError as e:
 assert 'Primary scientific artifact unavailable' in str(e)
 assert not (a.ROOT/'fresh').exists() and not (a.ROOT/'report.json').exists()
else: raise AssertionError('Fresh scientific audit requires primary cache')
"""
    result=subprocess.run([sys.executable,'-X','utf8','-B','-c',code],cwd=root,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
