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
