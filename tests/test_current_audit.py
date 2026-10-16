import json
import shutil
import subprocess
import sys

import pytest

from scripts import assess_chart_current as audit


def policy():return json.loads((audit.ROOT/audit.POLICY).read_text(encoding='utf-8'))


@pytest.mark.parametrize('category',['maximum','minimum','required_true'])
def test_every_current_tensor_and_cotangent_criterion_is_enforced(category):
    p=policy();m={**{k:v/2 for k,v in p['maximum'].items()},**{k:v*2 for k,v in p['minimum'].items()}};f={k:True for k in p['required_true']}
    assert audit.failures(m,f,p)==[]
    for key in p[category]:
        mm,ff=m.copy(),f.copy()
        if category=='required_true':ff[key]=False
        else:mm[key]=p[category][key]
        assert audit.failures(mm,ff,p)==[key]


def test_corrupt_primary_rejected(tmp_path,monkeypatch):
    p=policy();name=next(iter(p['primary_sha256']));target=tmp_path/name;target.parent.mkdir(parents=True);target.write_bytes(b'corrupted');monkeypatch.setattr(audit,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='Pinned primary'):audit.primary_hashes(p)


def test_fresh_output_paths_enforced_before_jobs(tmp_path,monkeypatch):
    root=tmp_path/'root';root.mkdir();old=root/'old.json';old.write_bytes(b'keep');monkeypatch.setattr(audit,'ROOT',root)
    def forbidden():raise AssertionError('Paths must be checked before jobs')
    monkeypatch.setattr(audit,'check_sources',forbidden)
    with pytest.raises(FileExistsError):audit.audit(work=root/'fresh',output=old)
    with pytest.raises(ValueError):audit.audit(work=tmp_path/'outside',output=root/'new.json')
    assert old.read_bytes()==b'keep' and not (root/'fresh').exists()


def test_offline_import_rejects_missing_primary_only_at_fresh_audit(tmp_path):
    root=tmp_path/'clean';root.mkdir()
    for name in audit.source_hashes():
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(audit.ROOT/name,target)
    code="""from scripts import assess_chart_current as a
try: a.audit(work=a.ROOT/'fresh',output=a.ROOT/'report.json')
except FileNotFoundError as e:
 assert 'Primary scientific artifact unavailable' in str(e)
 assert not (a.ROOT/'fresh').exists() and not (a.ROOT/'report.json').exists()
else: raise AssertionError('Missing primary cache must reject fresh audit')
"""
    result=subprocess.run([sys.executable,'-X','utf8','-B','-c',code],cwd=root,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
