"""Explicit 0.3.0 evidence mapping; historical replay never certifies the current product."""
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

MANIFEST = 'scripts/validation/release032-history.json'
MANIFEST_SHA = '4139358c23b68219216f43a402d2c6aaa449abac52b78e8e19db97cb47c9c4f0'
ARCHIVE = 'scripts/validation/release030-sources.zip'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def historical_sha(root, name, expected, *, cargo=False):
    """Allow only the recorded release transition, rejecting arbitrary live edits."""
    root = Path(root).resolve()
    path = (root/name).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Historical source escapes checkout')
    normalize = lambda data: data.replace(b'\r\n', b'\n') if cargo else data
    actual = digest(normalize(path.read_bytes()))
    if actual == expected:
        return actual
    raw = (root/MANIFEST).read_bytes()
    if digest(raw) != MANIFEST_SHA:
        raise ValueError('Changed release history manifest')
    manifest = json.loads(raw)
    row = manifest['files'].get(name)
    if (manifest['schema'] != 1 or manifest['archive'] != ARCHIVE or row is None
            or row['canonical_cargo'] is not cargo or row['old_sha256'] != expected
            or row['current_sha256'] != actual):
        raise ValueError('Changed historical source or Cargo content: '+name)
    archive = root/ARCHIVE
    if digest(archive.read_bytes()) != manifest['archive_sha256']:
        raise ValueError('Changed historical source archive')
    with ZipFile(archive) as saved:
        historical = digest(normalize(saved.read(name)))
    if historical != expected:
        raise ValueError('Historical source SHA differs: '+name)
    return historical


def historical_cargo_hashes(root, expected):
    return {name:historical_sha(root, name, sha, cargo=True)
            for name, sha in expected.items()}
