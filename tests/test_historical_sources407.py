"""Exact historical inputs, hostile artifacts and explicit metadata roles."""
import hashlib,json,shutil,tomllib
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import pytest
from scripts import historical_sources407 as saved
from scripts.release_history import historical_sha,ui_historical_sha,MANIFEST
ROOT=Path(__file__).resolve().parents[1]


def copy_snapshot(dest):
    for name in (saved.ARCHIVE,saved.MANIFEST):
        p=dest/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,p)


def test_entire_eight_member_closure_matches_original375_and_git_provenance():
    manifest,files=saved.read_sources(ROOT)
    old=json.loads((ROOT/'docs/current-runtime-375-validation.json').read_bytes())
    assert len(files)==8
    for name,raw in files.items():
        expected=saved.CONTROL_SHA if name==saved.CONTROL else old['source_sha256'][name]
        assert hashlib.sha256(raw).hexdigest()==expected
        provenance=manifest['files'][name]
        assert provenance['git_commit']==(manifest['pre404'] if name==saved.CONTROL else manifest['accepted032'])
        # Only an independent Git-object comparison; never alter raw SHA/bytes.
        assert hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()==provenance['git_blob_SHA256']
    for name,expected in manifest['control_row_receipts'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==expected


@pytest.mark.parametrize('damage',['byte','missing-member','current405','current407','wrong-commit','missing-archive','missing-manifest'])
def test_foreign_or_incomplete_history_rejected(tmp_path,damage):
    copy_snapshot(tmp_path)
    if damage=='wrong-commit':
        path=tmp_path/saved.MANIFEST;m=json.loads(path.read_bytes());m['pre404']='0'*40;path.write_text(json.dumps(m))
    elif damage.startswith('missing-') and damage!='missing-member':
        (tmp_path/(saved.ARCHIVE if damage=='missing-archive' else saved.MANIFEST)).unlink()
    else:
        path=tmp_path/saved.ARCHIVE
        with ZipFile(path) as z:files={n:z.read(n) for n in z.namelist()}
        if damage=='byte':files[saved.CONTROL]+=b'\n'
        elif damage=='missing-member':files.pop(saved.CONTROL)
        elif damage=='current405':
            raw=(ROOT/'tests/fixtures/control-row-405.py.txt').read_bytes()
            assert hashlib.sha256(raw).hexdigest()=='33c289f8716fb8a7e45f5d9775e3482a49c74650faa908a024d80358a3ee8026'
            files[saved.CONTROL]=raw
        else:files[saved.CONTROL]=(ROOT/saved.CONTROL).read_bytes()
        with ZipFile(path,'w',ZIP_DEFLATED) as z:
            for name,raw in files.items():z.writestr(name,raw)
    with pytest.raises((ValueError,FileNotFoundError)):saved.read_sources(tmp_path)


def test_old_ui_is_offline_only_current_guard_stays_strict(tmp_path):
    from scripts.ias15_process import verify_files
    from scripts.sandbox_checks.accept_sandbox import check_receipts
    copy_snapshot(tmp_path);path=tmp_path/saved.CONTROL;path.parent.mkdir(parents=True);path.write_bytes((ROOT/saved.CONTROL).read_bytes())
    assert ui_historical_sha(tmp_path,saved.CONTROL,saved.CONTROL_SHA)==saved.CONTROL_SHA
    assert path.read_bytes()==(ROOT/saved.CONTROL).read_bytes()
    with pytest.raises(ValueError,match='SHA mismatch'):verify_files({saved.CONTROL:saved.CONTROL_SHA},root=tmp_path)
    with pytest.raises(ValueError,match='source/input changed'):check_receipts(ROOT)
    with pytest.raises(ValueError,match='live source'):saved.restore_metadata032(ROOT,ROOT)


def assert_version(root,version):
    for name,table in [('pyproject.toml','project'),('rust/solar_core/Cargo.toml','package'),('rust/solar_native/Cargo.toml','package'),('rust/solar_native/pyproject.toml','project')]:
        assert tomllib.loads((root/name).read_text())[table]['version']==version
    for name in ('solar_core','solar_native'):
        packages=tomllib.loads((root/f'rust/{name}/Cargo.lock').read_text())['package']
        assert next(p['version'] for p in packages if p['name']==name)==version


def test_historical032_and_candidate033_cannot_exchange_metadata(tmp_path):
    old=tmp_path/'accepted032';new=tmp_path/'candidate033'
    saved.restore_metadata032(ROOT,old);assert_version(old,'0.3.2');assert_version(ROOT,'0.3.3')
    m,_=saved.read_sources(ROOT)
    for name in m['metadata032']:
        dst=new/name;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dst)
    assert_version(new,'0.3.3')
    for destination,source,version in ((old,new,'0.3.2'),(new,old,'0.3.3')):
        path=destination/'rust/solar_core/Cargo.toml';raw=path.read_bytes();path.write_bytes((source/'rust/solar_core/Cargo.toml').read_bytes())
        with pytest.raises(AssertionError):assert_version(destination,version)
        path.write_bytes(raw)
