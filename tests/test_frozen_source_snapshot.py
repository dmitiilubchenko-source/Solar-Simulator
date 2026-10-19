"""Historical source verification must retain exact SHA and path guards."""
import hashlib
from pathlib import Path
from zipfile import ZipFile

import pytest

from scripts import assess_nominal_jpl as audit


def setup_snapshot(tmp_path,monkeypatch):
    raw=(audit.ROOT/audit.SOURCE_SNAPSHOT).read_bytes()
    dest=tmp_path/audit.SOURCE_SNAPSHOT;dest.parent.mkdir(parents=True);dest.write_bytes(raw)
    with ZipFile(dest) as z:old=z.read('src/solar_simulator/app.py')
    monkeypatch.setattr(audit,'ROOT',tmp_path)
    return dest,hashlib.sha256(old).hexdigest()


@pytest.mark.parametrize('name',['src/solar_simulator/app.py','src\\solar_simulator\\app.py'])
def test_exact_archived_source_qualifies_history_while_live_source_is_different(tmp_path,monkeypatch,name):
    _,sha=setup_snapshot(tmp_path,monkeypatch)
    path=tmp_path/'src/solar_simulator/app.py';path.parent.mkdir(parents=True);path.write_bytes(b'new live UI')
    audit.verify_frozen_sources({name:sha})
    assert path.read_bytes()==b'new live UI'


@pytest.mark.parametrize('corruption',['archive','digest','unarchived','outside'])
def test_archival_verification_rejects_corruption_and_unrecorded_sources(tmp_path,monkeypatch,corruption):
    path,sha=setup_snapshot(tmp_path,monkeypatch)
    binding={'src/solar_simulator/app.py':sha}
    if corruption=='archive':path.write_bytes(path.read_bytes()+b'changed')
    elif corruption=='digest':binding={'src/solar_simulator/app.py':'0'*64}
    elif corruption=='unarchived':binding={'src/solar_simulator/relativity.py':sha}
    else:binding={'../outside.py':sha}
    with pytest.raises(ValueError):audit.verify_frozen_sources(binding)
