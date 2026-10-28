"""Recompute compact evidence, retain failed criteria and exact old-source bytes."""
from pathlib import Path
from zipfile import ZipFile
import pytest
from scripts.assess_two_q2_380 import audit,digest
from scripts.release_history import ROTATION_ARCHIVE,ROTATION_ARCHIVE_SHA,ui_historical_sha

ROOT=Path(__file__).resolve().parents[1]


def test_compact_arrays_and_original_failures_are_independently_recomputed():
    result=audit()
    assert result['original_arrays_unchanged'] and len(result['retained_FAIL'])==3


def test_frozen_artifacts_and_original_failed_worker_are_intact():
    import hashlib,json
    manifest=json.loads((ROOT/'docs/two-q2-380-manifest.json').read_bytes())
    for name,expected in manifest['artifacts'].items():
        if not name.endswith('.py'):assert digest(ROOT/name)==expected,name
    original=json.loads((ROOT/'scripts/two-q2-380-plan.json').read_bytes())
    with ZipFile(ROOT/'scripts/validation/two-q2-380-initial-scripts.zip') as archive:
        for name in archive.namelist():assert hashlib.sha256(archive.read(name)).hexdigest()==original['source_SHA256'][name]


@pytest.mark.parametrize('damage',['missing','corrupt'])
def test_historical_source_cannot_be_supplied_by_a_missing_or_changed_archive(tmp_path,damage):
    name='src/solar_simulator/nbody_rotation.py'
    with ZipFile(ROOT/ROTATION_ARCHIVE) as archive:expected=digest_bytes(archive.read(name))
    target=tmp_path/name;target.parent.mkdir(parents=True);target.write_text('changed current runtime',encoding='utf8')
    if damage=='corrupt':
        target=tmp_path/ROTATION_ARCHIVE;target.parent.mkdir(parents=True);target.write_bytes(b'not the fixed archive')
        with pytest.raises(ValueError,match='archive'):ui_historical_sha(tmp_path,name,expected)
    else:assert ui_historical_sha(tmp_path,name,expected)!=expected
    assert digest(ROOT/ROTATION_ARCHIVE)==ROTATION_ARCHIVE_SHA


def digest_bytes(value):
    import hashlib
    return hashlib.sha256(value).hexdigest()
