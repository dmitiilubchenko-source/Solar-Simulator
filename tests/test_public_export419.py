import json
from pathlib import Path
import pytest

def test_public_copy_removes_only_machine_metadata_and_keeps_numbers(tmp_path):
    from scripts.qualification419.public_export import export_public
    p=tmp_path/'docs/history.json';p.parent.mkdir()
    original={'path':'C:/Users/Admin/Desktop/result','failed':3,'value':1.2345678901234567}
    p.write_text(json.dumps(original))
    result=export_public(tmp_path)
    changed=json.loads(p.read_text())
    assert changed['value']==original['value'] and changed['failed']==3
    assert 'Admin' not in changed['path'] and result['files']

def test_never_rewrites_scientific_verification_or_runtime_code(tmp_path):
    from scripts.qualification419.public_export import export_public
    for path in ('verification/raw.json','runtime/Lib/a.py'):
        p=tmp_path/path;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text('C:/Users/Admin/private')
        with pytest.raises(ValueError):export_public(tmp_path)
        assert p.read_text()=='C:/Users/Admin/private'
        p.unlink()
