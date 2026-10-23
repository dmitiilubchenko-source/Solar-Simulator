"""Old evidence stays immutable and arbitrary current-source changes fail closed."""
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

import pytest

from scripts.release_history import ARCHIVE, MANIFEST, historical_sha

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def history(tmp_path):
    manifest = json.loads((ROOT/MANIFEST).read_bytes())
    for name in (ARCHIVE, MANIFEST, *manifest['files']):
        target = tmp_path/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    return tmp_path, manifest


def test_exact_historical_bytes_survive_product_version_transition(history):
    root, manifest = history
    with ZipFile(root/ARCHIVE) as archive:
        for name, row in manifest['files'].items():
            cargo = row['canonical_cargo']
            assert historical_sha(root, name, row['old_sha256'], cargo=cargo) == row['old_sha256']
            raw = archive.read(name)
            if cargo:raw = raw.replace(b'\r\n', b'\n')
            assert hashlib.sha256(raw).hexdigest() == row['old_sha256']


@pytest.mark.parametrize('damage', ['live', 'archive', 'manifest', 'unknown-sha'])
def test_changed_release_evidence_is_rejected(history, damage):
    root, manifest = history
    name = 'rust/solar_core/Cargo.toml'
    expected = manifest['files'][name]['old_sha256']
    if damage == 'unknown-sha':expected = '0'*64
    else:
        path = root/({'live':name, 'archive':ARCHIVE, 'manifest':MANIFEST}[damage])
        path.write_bytes(path.read_bytes()+b'changed')
    with pytest.raises(ValueError):historical_sha(root, name, expected, cargo=True)


def test_cargo_checkout_line_endings_are_allowed_but_content_is_not(history):
    root, manifest = history
    name = 'rust/solar_core/Cargo.toml'
    path = root/name
    expected = manifest['files'][name]['old_sha256']
    for ending in (b'\n', b'\r\n'):
        path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', ending))
        assert historical_sha(root, name, expected, cargo=True) == expected
    path.write_bytes(path.read_bytes()+b'content')
    with pytest.raises(ValueError):historical_sha(root, name, expected, cargo=True)


@pytest.mark.parametrize('ending', [b'\n', b'\r\n'])
def test_entire_mapped_closure_survives_linux_and_windows_cargo_checkout(history, ending):
    root, manifest = history
    for name, row in manifest['files'].items():
        path = root/name
        if name.endswith(('.toml', '.lock')):
            path.write_bytes(path.read_bytes().replace(b'\r\n', b'\n').replace(b'\n', ending))
        assert historical_sha(root, name, row['old_sha256'], cargo=row['canonical_cargo']) == row['old_sha256']
    # These files are preserved as raw provenance, not resolved by old scientific replayers.
    assert 'pyproject.toml' not in manifest['files']
    assert 'rust/solar_native/pyproject.toml' not in manifest['files']
    with ZipFile(root/ARCHIVE) as archive:
        assert b'0.3.0' in archive.read('pyproject.toml')
        assert b'0.3.0' in archive.read('rust/solar_native/pyproject.toml')
