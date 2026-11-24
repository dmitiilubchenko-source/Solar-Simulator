"""Explicit immutable historical JPL data input, never current-source qualification."""
from hashlib import sha256
import json
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

import pytest

ROOT = Path(__file__).resolve().parents[1]


def fixture_archive(path, damage=None):
    with ZipFile(ROOT / 'tests/data/jpl-verification.zip') as z:
        payloads = {name: z.read(name) for name in z.namelist()}
    if damage == 'missing': del payloads['reference.json']
    if damage == 'changed': payloads['reference.json'] += b'corruption'
    if damage == 'unexpected': payloads['extra.txt'] = b'unlisted'
    if damage == 'traversal': payloads['../outside.txt'] = b'escape'
    if damage == 'duplicate_root': payloads['other'] = b'irrelevant'
    with ZipFile(path, 'w', ZIP_DEFLATED) as z:
        for name, raw in payloads.items(): z.writestr('old/verification/' + name, raw)
        if damage == 'duplicate_root': z.writestr('second/verification/manifest.json', b'{}')
    return sha256(path.read_bytes()).hexdigest()


def test_exact_old_bundle_replays_without_solar_solver_and_preserves_bytes(tmp_path, monkeypatch):
    from scripts.build_portable import reuse_historical_verification
    import solar_simulator.experiment as experiment
    monkeypatch.setattr(experiment, 'advance', lambda *a, **kw: pytest.fail('No orbit calculation'))
    archive = tmp_path / 'old.zip'; digest = fixture_archive(archive)
    before = archive.read_bytes(); output = tmp_path / 'new verification'
    result = reuse_historical_verification(archive, digest, output)
    assert result['checks_passed'] and result['origin']['current_runtime_qualified'] is False
    assert result['origin']['archive_sha256'] == digest and archive.read_bytes() == before
    with ZipFile(archive) as z:
        for name in z.namelist():
            assert (output / name.removeprefix('old/verification/')).read_bytes() == z.read(name)


@pytest.mark.parametrize('damage', ['missing', 'changed', 'unexpected', 'traversal', 'duplicate_root', 'sha'])
def test_invalid_bundle_rejects_before_creating_destination(tmp_path, damage):
    from scripts.build_portable import reuse_historical_verification
    archive = tmp_path / 'old.zip'; digest = fixture_archive(archive, damage)
    if damage == 'sha': digest = '0' * 64
    original = archive.read_bytes(); output = tmp_path / 'not created'
    with pytest.raises((ValueError, FileNotFoundError)):
        reuse_historical_verification(archive, digest, output)
    assert not output.exists() and archive.read_bytes() == original


def test_existing_destination_and_incomplete_option_pair_refuse(tmp_path):
    from scripts.build_portable import build, reuse_historical_verification
    archive = tmp_path / 'old.zip'; digest = fixture_archive(archive)
    output = tmp_path / 'existing'; output.mkdir(); (output / 'keep').write_bytes(b'keep')
    with pytest.raises(FileExistsError): reuse_historical_verification(archive, digest, output)
    assert (output / 'keep').read_bytes() == b'keep'
    with pytest.raises(ValueError, match='together'): build(verification_archive=archive)


def test_direct_script_import_has_its_own_project_root(tmp_path):
    import subprocess
    import sys
    archive = tmp_path / 'old.zip'; digest = fixture_archive(archive)
    code = '''
import runpy, sys
module = runpy.run_path(sys.argv[1], run_name='test_builder_entry')
result = module['reuse_historical_verification'](sys.argv[2], sys.argv[3], sys.argv[4])
assert result['checks_passed']
'''
    process = subprocess.run([sys.executable, '-I', '-B', '-c', code,
        str(ROOT / 'scripts/build_portable.py'), str(archive), digest, str(tmp_path / 'copied')],
        cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert process.returncode == 0, process.stdout + process.stderr
