"""Portable INTERNAL evidence paths; current qualification always remains strict."""
from pathlib import Path
import pytest


@pytest.mark.parametrize('name',['scripts/example.json',r'scripts\example.json'])
def test_evidence_paths_resolve_the_same_internal_file(tmp_path,name):
    from scripts.release_history import evidence_path
    target=tmp_path/'scripts/example.json';target.parent.mkdir();target.write_bytes(b'exact historical bytes\r\n')
    before=target.read_bytes()
    assert evidence_path(tmp_path,name)==target.resolve()
    assert evidence_path(tmp_path,name).read_bytes()==before


@pytest.mark.parametrize('name',['../outside.json',r'..\outside.json',r'C:\other\file.json',
    r'\outside.json',r'\\server\share\file.json','/outside.json','',r'C:relative.json'])
def test_evidence_paths_cannot_escape_checkout(tmp_path,name):
    from scripts.release_history import evidence_path
    with pytest.raises(ValueError):evidence_path(tmp_path,name)


def test_source_input_audit_explicitly_does_not_qualify_an_environment():
    from scripts.sandbox_checks.accept_sandbox import audit_receipt_inputs
    # Current checkout must fail before producing ANY success result.
    with pytest.raises(ValueError,match='Scientific receipt source/input changed'):
        audit_receipt_inputs()
