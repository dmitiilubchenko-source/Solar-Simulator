import hashlib
import json
from pathlib import Path
import zipfile

import pytest

from scripts.prepare_test_inputs import PATHS, ROOT, restore


def test_public_inputs_restore_all_expected_bytes_and_preserve_existing_files(tmp_path):
    assert restore(tmp_path)==dict(restored=7,verified=7)
    expected=json.loads((ROOT/"tests/data/research63-inputs.json").read_text())
    stamps={}
    for name in PATHS:
        path=tmp_path/name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected["files"][name]
        stamps[name]=path.stat().st_mtime_ns
    assert restore(tmp_path)==dict(restored=0,verified=7)
    assert all((tmp_path/name).stat().st_mtime_ns==stamp for name,stamp in stamps.items())


def test_corrupted_existing_input_rejected_before_restoring_any_other_file(tmp_path):
    path=tmp_path/PATHS[-1];path.parent.mkdir(parents=True);path.write_bytes(b"corrupted")
    with pytest.raises(ValueError,match="Corrupted existing"):restore(tmp_path)
    assert path.read_bytes()==b"corrupted"
    assert not (tmp_path/PATHS[0]).exists()


def test_corrupted_public_archive_is_rejected_before_creating_inputs(tmp_path):
    archive=tmp_path/"bad.zip";archive.write_bytes(b"invalid")
    with pytest.raises(ValueError,match="bundle SHA256"):restore(tmp_path,bundle=archive)
    assert not (tmp_path/".tools").exists()


def test_unexpected_archive_path_is_rejected_even_with_matching_archive_digest(tmp_path):
    archive=tmp_path/"escape.zip"
    with zipfile.ZipFile(archive,"w") as output:output.writestr("../../escape.json","bad")
    document=json.loads((ROOT/"tests/data/research63-inputs.json").read_text())
    document["bundle_sha256"]=hashlib.sha256(archive.read_bytes()).hexdigest()
    manifest=tmp_path/"manifest.json";manifest.write_text(json.dumps(document))
    with pytest.raises(ValueError,match="members"):restore(tmp_path,bundle=archive,manifest=manifest)
    assert not (tmp_path/".tools").exists() and not (tmp_path.parent/"escape.json").exists()


@pytest.mark.parametrize("version",[True,2])
def test_unknown_manifest_version_is_rejected(tmp_path,version):
    document=json.loads((ROOT/"tests/data/research63-inputs.json").read_text())
    document["version"]=version
    manifest=tmp_path/"manifest.json";manifest.write_text(json.dumps(document))
    with pytest.raises(ValueError,match="manifest"):restore(tmp_path,manifest=manifest)
    assert not (tmp_path/".tools").exists()
