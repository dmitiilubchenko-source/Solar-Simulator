"""Historical UI bytes must never authorize a live worker or changed science."""
import hashlib
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts.release_history import UI_ARCHIVE,UI_ARCHIVE_SHA,UI_FILES,ui_historical_sha


def setup_archive(tmp_path,name='src/solar_simulator/app.py'):
    root=Path(__file__).resolve().parents[1]
    raw=(root/UI_ARCHIVE).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==UI_ARCHIVE_SHA
    archive=tmp_path/UI_ARCHIVE;archive.parent.mkdir(parents=True);archive.write_bytes(raw)
    with ZipFile(archive) as saved:expected=hashlib.sha256(saved.read(name)).hexdigest()
    live=tmp_path/name;live.parent.mkdir(parents=True,exist_ok=True);live.write_bytes(b'changed live source')
    return archive,live,expected


@pytest.mark.parametrize('name',UI_FILES)
def test_exact_ui_snapshot_preserves_old_binding_without_qualifying_live(tmp_path,name):
    _,live,expected=setup_archive(tmp_path,name)
    assert ui_historical_sha(tmp_path,name,expected)==expected
    assert live.read_bytes()==b'changed live source'


@pytest.mark.parametrize('damage',['bytes','missing','digest','unlisted','escape'])
def test_ui_history_rejects_damage_or_unrecorded_bindings(tmp_path,damage):
    archive,live,expected=setup_archive(tmp_path)
    name='src/solar_simulator/app.py'
    if damage=='bytes':
        archive.write_bytes(archive.read_bytes()+b'changed')
        with pytest.raises(ValueError,match='archive'):ui_historical_sha(tmp_path,name,expected)
    elif damage=='missing':
        archive.unlink()
        with pytest.raises(OSError):ui_historical_sha(tmp_path,name,expected)
    elif damage=='escape':
        with pytest.raises(ValueError,match='escapes'):ui_historical_sha(tmp_path,'../app.py',expected)
    else:
        if damage=='digest':expected='0'*64
        else:
            name='src/solar_simulator/simulation.py'
            (tmp_path/name).write_bytes(live.read_bytes())
        assert ui_historical_sha(tmp_path,name,expected)!=expected


def test_live_process_guard_stays_strict_even_with_available_snapshot(tmp_path):
    from scripts.ias15_process import verify_files
    _,_,expected=setup_archive(tmp_path)
    name='src/solar_simulator/app.py'
    assert ui_historical_sha(tmp_path,name,expected)==expected
    with pytest.raises(ValueError,match='SHA mismatch'):verify_files({name:expected},root=tmp_path)
