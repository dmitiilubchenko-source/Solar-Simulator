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
        assert ui_historical_sha(tmp_path,name,expected) != expected
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


@pytest.mark.parametrize('missing_live', [False, True])
def test_shared_archive_name_does_not_require_unrelated_ui_archive(tmp_path, missing_live):
    from scripts.release_history import NUMERIC_ARCHIVE, NUMERIC_ARCHIVE_SHA
    root=Path(__file__).resolve().parents[1];name='scripts/release_history.py'
    raw=(root/NUMERIC_ARCHIVE).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==NUMERIC_ARCHIVE_SHA
    target=tmp_path/NUMERIC_ARCHIVE;target.parent.mkdir(parents=True);target.write_bytes(raw)
    with ZipFile(target) as saved:expected=hashlib.sha256(saved.read(name)).hexdigest()
    if not missing_live:(tmp_path/name).write_bytes(b'changed current resolver')
    assert not (tmp_path/UI_ARCHIVE).exists()
    assert ui_historical_sha(tmp_path,name,expected)==expected
    assert ui_historical_sha(tmp_path,name,'0'*64)!=expected
    target.write_bytes(raw+b'corrupted')
    with pytest.raises(ValueError,match='Changed historical source archive'):
        ui_historical_sha(tmp_path,name,expected)


@pytest.mark.parametrize('relative', [False, True])
def test_history_read_never_grants_current_checkpoint_execution(relative, monkeypatch):
    import json
    from scripts import canonical_checkpoint as cart, relative_canonical_checkpoint as rel
    from scripts.release_history import verify_checkpoint_history
    root=Path(__file__).resolve().parents[1];core=rel if relative else cart
    path='.tools/rotation63/initial.json' if relative else json.loads(
        (root/'scripts/canonical-solar-policy.json').read_text())['input_checkpoint']
    before=(root/path).read_bytes();cp=core.load(root/path)
    verify_checkpoint_history(cp,root)
    with pytest.raises(ValueError,match='source hashes missing'):
        core.verify_sources(cp,root)
    def forbidden(*args,**kwargs):pytest.fail('historical state reached current solver')
    monkeypatch.setattr(core,'solve_ivp',forbidden)
    with pytest.raises(ValueError,match='loaded'):
        core.evolve(cp,[0.,.001],source_root=root)
    assert (root/path).read_bytes()==before
