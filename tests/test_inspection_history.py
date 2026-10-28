"""Reporting compatibility is historical provenance, never current authorization."""
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from scripts.release_history import INSPECTION_ARCHIVE,ui_historical_sha

ROOT=Path(__file__).resolve().parents[1]
NAME='src/solar_simulator/commands.py'


@pytest.fixture
def saved_context(tmp_path):
    from scripts.check_runtime_reliability376 import PROTOCOL,read
    target=tmp_path/NAME;target.parent.mkdir(parents=True);shutil.copyfile(ROOT/NAME,target)
    archive=tmp_path/INSPECTION_ARCHIVE;archive.parent.mkdir(parents=True);shutil.copyfile(ROOT/INSPECTION_ARCHIVE,archive)
    expected=read(PROTOCOL)['source_SHA256'][NAME]
    assert ui_historical_sha(tmp_path,NAME,expected)==expected
    return tmp_path,archive,expected


def test_missing_reporting_archive_cannot_supply_historical_provenance(saved_context):
    root,archive,expected=saved_context;archive.unlink()
    assert ui_historical_sha(root,NAME,expected)!=expected


def test_corrupted_reporting_archive_is_rejected(saved_context):
    root,archive,expected=saved_context;archive.write_bytes(archive.read_bytes()+b'bad')
    with pytest.raises(ValueError,match='Changed historical source archive'):ui_historical_sha(root,NAME,expected)


@pytest.mark.parametrize('bad',[1,'false',None])
def test_historical_mode_requires_explicit_boolean(bad):
    from scripts.assess_runtime_reliability376 import verify
    with pytest.raises(ValueError,match='explicit bool'):verify(historical=bad)


def test_historical_flag_is_never_a_build_authorization():
    p=subprocess.run([sys.executable,'-X','utf8','-B','-m','scripts.assess_runtime_reliability376','build','--historical'],
        cwd=ROOT,timeout=15,capture_output=True,text=True,encoding='utf8')
    assert p.returncode==2 and '--historical is only valid' in p.stderr
