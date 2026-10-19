"""Release-artifact selection and the real isolated GUI/restart acceptance probe."""
import json
import os
from pathlib import Path
import subprocess
import sys

from packaging.tags import sys_tags
import pytest

from scripts.build_portable import candidate_versions, select_native_wheel


def wheel(directory, version, *, build='', tag=None):
    tag = tag or str(next(sys_tags()))
    path = directory/f'solar_native-{version}-{build}{tag}.whl'
    path.write_bytes(b'filename-selection fixture, not a built binary')
    return path


def test_artifact_selection_ignores_newer_wrong_version_and_wrong_abi(tmp_path):
    current = wheel(tmp_path, '0.3.0rc1')
    stale = wheel(tmp_path, '0.2.0')
    os.utime(stale, (current.stat().st_mtime+3600,)*2)
    wheel(tmp_path, '0.3.0rc1', tag='cp00-cp00-impossible')
    assert select_native_wheel(tmp_path, '0.3.0-rc.1') == current


def test_missing_or_ambiguous_candidate_is_an_explicit_error(tmp_path):
    wheel(tmp_path, '0.2.0')
    with pytest.raises(ValueError, match='found 0'):
        select_native_wheel(tmp_path, '0.3.0rc1')
    wheel(tmp_path, '0.3.0rc1')
    wheel(tmp_path, '0.3.0rc1', build='1-')
    with pytest.raises(ValueError, match='found 2'):
        select_native_wheel(tmp_path, '0.3.0rc1')


@pytest.mark.parametrize('stale', ['rust/solar_core/Cargo.toml', 'rust/solar_native/pyproject.toml'])
def test_paired_metadata_accepts_normalized_candidate_and_rejects_stale_component(tmp_path, stale):
    (tmp_path/'pyproject.toml').write_text('[project]\nversion="0.3.0rc1"\n')
    for name in ('solar_core', 'solar_native'):
        path = tmp_path/f'rust/{name}/Cargo.toml'
        path.parent.mkdir(parents=True)
        path.write_text('[package]\nversion="0.3.0-rc.1"\n')
    (tmp_path/'rust/solar_native/pyproject.toml').write_text('[project]\nversion="0.3.0rc1"\n')
    assert candidate_versions(tmp_path)[0] == '0.3.0rc1'
    table = 'project' if stale.endswith('pyproject.toml') else 'package'
    (tmp_path/stale).write_text(f'[{table}]\nversion="0.2.0"\n')
    with pytest.raises(ValueError, match='versions disagree'):
        candidate_versions(tmp_path)


def test_new_workflows_across_real_isolated_processes(tmp_path):
    """This validates the acceptance probe; actual ZIP acceptance remains separate."""
    script = Path(__file__).resolve().parents[1]/'scripts/portable_workflows.py'
    env = os.environ.copy()
    env['LOCALAPPDATA'] = str(tmp_path/'user data')
    for phase in ('create', 'restore'):
        process = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-I', str(script), phase],
                                 cwd=tmp_path, env=env, capture_output=True, text=True,
                                 encoding='utf-8', timeout=240)
        assert process.returncode == 0, process.stdout+process.stderr
        report = json.loads(process.stdout)
        assert report['isolated'] == 1
    assert set(report['results']) == {'python', 'rust'}
    assert report['physical_accuracy_claim'] is False


@pytest.mark.parametrize('fail', [False, True])
def test_build_smokes_share_owned_profile_and_cleanup_without_touching_caller(tmp_path, monkeypatch, fail):
    from scripts import build_portable as builder
    root = tmp_path/'source'
    root.mkdir()
    output = tmp_path/'future ZIP'
    output.mkdir()
    caller = tmp_path/'caller user data'
    caller.mkdir()
    sentinel = caller/'keep.json'
    sentinel.write_bytes(b'actual user data must survive')
    monkeypatch.setattr(builder, 'ROOT', root)
    monkeypatch.setenv('LOCALAPPDATA', str(caller))
    for key in ('PYTHONHOME', 'PYTHONPATH', 'TCL_LIBRARY', 'TK_LIBRARY', 'MPLCONFIGDIR'):
        monkeypatch.setenv(key, str(caller/'do not use'))
    parent_environment = dict(os.environ)
    create = '''
import json,os,pathlib
from solar_simulator.recovery import save_recovery
from solar_simulator.experiment import preset
assert not any(name in os.environ for name in ('PYTHONHOME','PYTHONPATH','TCL_LIBRARY','TK_LIBRARY'))
path=save_recovery(preset('sun-earth'),reason='closed')
pathlib.Path('smoke-receipt.json').write_text(json.dumps(dict(
    profile=os.environ['LOCALAPPDATA'],matplotlib=os.environ['MPLCONFIGDIR'],recovery=str(path))))
'''
    restore = f'''
import json,os,pathlib,sys
from solar_simulator.storage import load
receipt=json.loads(pathlib.Path('smoke-receipt.json').read_text())
assert receipt['profile']==os.environ['LOCALAPPDATA']
assert load(receipt['recovery']).time==0
sys.exit({7 if fail else 0})
'''
    if fail:
        with pytest.raises(subprocess.CalledProcessError) as caught:
            builder.run_build_smokes(Path(sys.executable), output, (create, restore))
        assert caught.value.returncode == 7
    else:
        builder.run_build_smokes(Path(sys.executable), output, (create, restore))
    receipt = json.loads((output/'smoke-receipt.json').read_text())
    profile = Path(receipt['profile'])
    assert profile.is_relative_to(root/'.tools') and not profile.is_relative_to(output)
    assert Path(receipt['matplotlib']).parent == profile.parent
    assert not profile.parent.exists() and list((root/'.tools').iterdir()) == []
    assert list(caller.iterdir()) == [sentinel] and sentinel.read_bytes() == b'actual user data must survive'
    assert dict(os.environ) == parent_environment
