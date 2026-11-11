"""Version407V: separate live040 from immutable032/033; no new physics."""
from pathlib import Path
import ast,hashlib,shutil,subprocess
import pytest
from scripts.build_portable import candidate_versions
from scripts.historical_sources407 import restore_metadata032
from historical033_fixture407v import restore033
from test_historical_sources407 import assert_version
ROOT=Path(__file__).resolve().parents[1]
BASE='828c79805f7db4576b474206923285ce0b4541c4'
META=('pyproject.toml','rust/solar_core/Cargo.toml','rust/solar_native/Cargo.toml','rust/solar_native/pyproject.toml','rust/solar_core/Cargo.lock','rust/solar_native/Cargo.lock')
def test_live040_metadata():
    assert_version(ROOT,'0.4.0')
    assert candidate_versions(ROOT)==('0.4.0',{'solar_core':'0.4.0','solar_native':'0.4.0'})
@pytest.mark.parametrize('version',['0.3.2','0.3.3'])
@pytest.mark.parametrize('direction',['historical_into_live','live_into_historical'])
def test_current_historical_metadata_substitution_rejected(tmp_path,version,direction):
    old=tmp_path/'old';new=tmp_path/'new'
    (restore_metadata032(ROOT,old) if version=='0.3.2' else restore033(old))
    for n in META:
        p=new/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,p)
    destination,source,expected=(new,old,'0.4.0') if direction=='historical_into_live' else (old,new,version)
    for n in META:shutil.copyfile(source/n,destination/n)
    with pytest.raises(AssertionError):assert_version(destination,expected)
def test_cargo_python_mismatch_rejected(tmp_path):
    for n in META:
        p=tmp_path/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,p)
    p=tmp_path/'rust/solar_core/Cargo.toml';p.write_bytes(p.read_bytes().replace(b'0.4.0',b'0.3.3'))
    with pytest.raises(ValueError,match='disagree'):candidate_versions(tmp_path)
def test_immutable033_archive_corruption_rejected(tmp_path,monkeypatch):
    import historical033_fixture407v as f
    path=tmp_path/'bad.zip';path.write_bytes(f.ARCHIVE.read_bytes()+b'x');monkeypatch.setattr(f,'ARCHIVE',path)
    with pytest.raises(ValueError,match='SHA'):restore033(tmp_path/'isolated')
def test_warning_has_exactly_one_status_delta():
    p='src/solar_simulator/inspection.py'
    old=subprocess.check_output(['git','show',BASE+':'+p],cwd=ROOT)
    new=(ROOT/p).read_bytes().replace(b'\r\n',b'\n')
    assert new==old.replace('Release0.3.3 — NO-GO.'.encode(),'Solar-Simulator 0.4.0 — кандидат, выпуск не разрешён.'.encode())
    def normalized(raw):
        tree=ast.parse(raw)
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,str):node.value=node.value.replace('Release0.3.3 — NO-GO.','STATUS').replace('Solar-Simulator 0.4.0 — кандидат, выпуск не разрешён.','STATUS')
        return ast.dump(tree)
    assert normalized(old)==normalized(new)
def test_required_release040_doc_present_and_unreleased():
    text=(ROOT/'docs/releases/v0.4.0.md').read_text(encoding='utf8')
    assert 'UNRELEASED / RELEASE CANDIDATE' in text
    assert all(x in text for x in ['0.244795','10/11','11/11','FAIL380','FAIL402','NO-GO'])
