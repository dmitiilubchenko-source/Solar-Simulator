"""Reject physics, lifecycle, storage and native changes in a text-only patch."""
import hashlib
import pytest
from scripts.qualification405.check import require_inventory
from scripts.q2_text_delta403 import compare
from scripts.q2_source_adapter396 import require_sha

@pytest.mark.parametrize('path', ['src/solar_simulator/nbody_rotation.py',
    'src/solar_simulator/app.py', 'src/solar_simulator/storage.py', 'rust/solar_native/src/lib.rs'])
def test_unrelated_source_change_rejected(path):
    old = {'src/solar_simulator/inspection.py':'old',path:'fixed'}
    new = dict(old, **{'src/solar_simulator/inspection.py':'new',path:'changed'})
    with pytest.raises(ValueError):require_inventory(old,new)

def test_native_bytes_cannot_be_relabelled(tmp_path):
    p=tmp_path/'native.pyd';p.write_bytes(b'qualified');expected=hashlib.sha256(p.read_bytes()).hexdigest()
    require_sha(p,expected);p.write_bytes(b'changed')
    with pytest.raises(ValueError):require_sha(p,expected)

def test_extra_import_or_callback_rejected():
    base=b"TWO_Q2_EXPERIMENTAL_WARNING='old'\ndef callback():return 1\n"
    for bad in (b'import os\n'+base,base.replace(b'return 1',b'return 2')):
        with pytest.raises(ValueError):compare(base,bad)

def test_one_literal_is_the_only_permitted_delta():
    base=b"TWO_Q2_EXPERIMENTAL_WARNING='old'\ndef callback():return 1\n"
    assert compare(base,base.replace(b"'old'",b"'new'"))['all_other_AST_and_bytes_exact']
