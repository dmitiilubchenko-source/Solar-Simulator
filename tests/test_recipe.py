"""IO failures use a small fingerprint stub; real fresh-process replay below does not."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from solar_simulator import recipe, trajectory
from solar_simulator.experiment import Settings, create_experiment
from solar_simulator.sandbox import branch_experiment, _canonical
from solar_simulator.simulation import Body
from solar_simulator.vector3 import Vector3


@pytest.fixture
def small_fingerprint(monkeypatch):
    fingerprint = dict(application_version='test-fixture', package_files={'a.py': 'a'*64})
    monkeypatch.setattr(recipe, 'runtime_fingerprint', lambda backend: fingerprint.copy())
    return fingerprint


def ballistic(integrator='dop853', backend='python'):
    return create_experiment([Body('free', 1., Vector3(3., 4., 5.), Vector3(2., -1., .5))],
                             Settings(10., integrator=integrator, backend=backend))


def reseal(path, payload):
    path.write_text(json.dumps(dict(payload=payload, sha256=hashlib.sha256(_canonical(payload).encode('utf-8')).hexdigest())),
                    encoding='utf-8')


def test_recipe_binds_full_initial_branch_and_actual_fractional_packets(tmp_path, small_fingerprint):
    branch = branch_experiment(ballistic())
    trajectory.record_trajectory(branch.child, tmp_path/'source', 25.25, packet_steps=2,
                                 parent_snapshot=branch.parent_snapshot)
    track = trajectory.Trajectory(tmp_path/'source')
    payload = recipe.read_recipe(track)
    assert payload['stable'] and payload['packet_boundaries_seconds'] == [[0., 20.], [20., 25.25]]
    assert payload['recording']['packet_steps'] == 2
    assert track.frame(0)[1] == branch.parent_snapshot
    before = {p.name: p.read_bytes() for p in track.directory.iterdir()}
    result = recipe.replay_trajectory(track.directory, tmp_path/'repeat')
    assert result['reproduced_prefix'] and not result['mismatched_frames']
    assert before == {p.name: p.read_bytes() for p in track.directory.iterdir()}


@pytest.mark.parametrize('status', ['stopped', 'failed'])
def test_prefix_replays_original_global_target_without_promoting_completion(tmp_path, monkeypatch, small_fingerprint, status):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path/'appdata'))
    compute = trajectory.advance_towards
    calls = 0
    def failing(*args):
        nonlocal calls
        calls += 1
        if calls > 1:
            raise RuntimeError('controlled compute error')
        return compute(*args)
    stop_calls = 0
    def stop():
        nonlocal stop_calls
        stop_calls += 1
        return stop_calls > 1
    if status == 'failed':
        monkeypatch.setattr(trajectory, 'advance_towards', failing)
        with pytest.raises(RuntimeError, match='recovery'):
            trajectory.record_trajectory(ballistic(), tmp_path/'source', 100., packet_steps=2)
        monkeypatch.setattr(trajectory, 'advance_towards', compute)
    else:
        trajectory.record_trajectory(ballistic(), tmp_path/'source', 100., packet_steps=2, stop_requested=stop)
    captured = []
    def observe(state, target, batch):
        captured.append((state.time, target, batch))
        return compute(state, target, batch)
    monkeypatch.setattr(trajectory, 'advance_towards', observe)
    result = recipe.replay_trajectory(tmp_path/'source', tmp_path/'repeat')
    assert captured == [(0., 100., 2)]
    assert result['reproduced_prefix'] and result['source_status'] == status and result['replay_status'] == 'stopped'
    assert result['last_committed_time_seconds'] == 20. and result['requested_target_seconds'] == 100.


def test_legacy_recording_still_plays_but_cannot_claim_provenance(tmp_path, small_fingerprint):
    trajectory.record_trajectory(ballistic(), tmp_path/'source', 20.)
    (tmp_path/'source/recipe.json').unlink()
    assert trajectory.Trajectory(tmp_path/'source').times == (0., 20.)
    with pytest.raises(ValueError, match='нет recipe'):
        recipe.replay_trajectory(tmp_path/'source', tmp_path/'repeat')
    assert not (tmp_path/'repeat').exists()


def test_unverifiable_dependency_inventory_is_not_declared_compatible(tmp_path, monkeypatch, small_fingerprint):
    fingerprint = dict(small_fingerprint, dependencies={
        'numpy': dict(version='editable-fixture', files={}, inventory_complete=False)})
    monkeypatch.setattr(recipe, 'runtime_fingerprint', lambda backend: fingerprint)
    trajectory.record_trajectory(ballistic(), tmp_path/'source', 25.25, packet_steps=2)
    audit = recipe.audit_recipe(trajectory.Trajectory(tmp_path/'source'))
    assert not audit['compatible'] and 'dependency-inventory-unverified' in audit['differences']
    with pytest.raises(ValueError, match='несовместимы'):
        recipe.replay_trajectory(tmp_path/'source', tmp_path/'repeat')
    assert not (tmp_path/'repeat').exists()


def test_editable_dependency_is_unverified_without_exporting_private_location(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from pathlib import PurePosixPath
    source = tmp_path/'fixture.py'
    source.write_text('# fixture\n', encoding='utf-8')
    distribution = SimpleNamespace(version='fixture', files=[PurePosixPath('fixture.py')], requires=[],
        locate_file=lambda path: source,
        read_text=lambda name: json.dumps(dict(url=str(tmp_path/'private working tree'), dir_info=dict(editable=True))))
    monkeypatch.setattr(recipe.metadata, 'distribution', lambda name: distribution)
    dependencies = recipe._dependencies()
    assert all(not item['inventory_complete'] for item in dependencies.values())
    assert str(tmp_path) not in json.dumps(dependencies)


@pytest.mark.parametrize('damage', ['sha', 'version', 'manifest', 'bounds', 'fingerprint', 'incomplete'])
def test_corrupt_incompatible_and_incomplete_recipes_fail_before_output(tmp_path, small_fingerprint, damage):
    trajectory.record_trajectory(ballistic(), tmp_path/'source', 25.25, packet_steps=2)
    path = tmp_path/'source/recipe.json'
    document = json.loads(path.read_bytes())
    payload = document['payload']
    if damage == 'sha':
        document['sha256'] = '0'*64
        path.write_text(json.dumps(document), encoding='utf-8')
    else:
        if damage == 'version':
            payload['schema_version'] = 99
        elif damage == 'manifest':
            payload['recording']['packet_steps'] = 1
        elif damage == 'bounds':
            payload['packet_boundaries_seconds'][0][1] = 19.
        elif damage == 'fingerprint':
            payload['fingerprint_start']['application_version'] = 'other'
            payload['fingerprint_end']['application_version'] = 'other'
        else:
            payload['fingerprint_end'] = None
        reseal(path, payload)
    with pytest.raises(ValueError):
        recipe.replay_trajectory(tmp_path/'source', tmp_path/'repeat')
    assert not (tmp_path/'repeat').exists()


def test_environment_drift_is_not_success_and_latest_state_has_recovery(tmp_path, monkeypatch, small_fingerprint):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path/'appdata'))
    calls = 0
    def drifting(backend):
        nonlocal calls
        calls += 1
        return dict(version='before' if calls == 1 else 'after')
    monkeypatch.setattr(recipe, 'runtime_fingerprint', drifting)
    with pytest.raises(RuntimeError, match='изменились.*recovery'):
        trajectory.record_trajectory(ballistic(), tmp_path/'source', 25.25, packet_steps=2)
    track = trajectory.Trajectory(tmp_path/'source')
    assert track.times[-1] == 25.25 and track.metadata['status'] == 'failed'
    assert not recipe.read_recipe(track)['stable']
    from solar_simulator.branch_io import open_experiment
    recovery = next((tmp_path/'appdata').rglob('checkpoint.json'))
    assert open_experiment(recovery)[0].time == 25.25


def test_cleanup_cannot_erase_an_already_observed_environment_drift(tmp_path, monkeypatch, small_fingerprint):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path/'appdata'))
    snapshots = iter([dict(version='before'), dict(version='after'), dict(version='before')])
    monkeypatch.setattr(recipe, 'runtime_fingerprint', lambda backend: next(snapshots))
    with pytest.raises(RuntimeError, match='изменились'):
        trajectory.record_trajectory(ballistic(), tmp_path/'source', 25.25, packet_steps=2)
    assert not recipe.read_recipe(trajectory.Trajectory(tmp_path/'source'))['stable']


def test_recipe_write_failure_keeps_published_data_and_recovery(tmp_path, monkeypatch, small_fingerprint):
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path/'appdata'))
    write = recipe._write_document
    def fail_final(document, path):
        if document['payload']['fingerprint_end'] is not None:
            raise OSError('controlled recipe write error')
        write(document, path)
    monkeypatch.setattr(recipe, '_write_document', fail_final)
    with pytest.raises(RuntimeError, match='recipe.*recovery'):
        trajectory.record_trajectory(ballistic(), tmp_path/'source', 25.25, packet_steps=2)
    track = trajectory.Trajectory(tmp_path/'source')
    assert track.times[-1] == 25.25
    assert list((tmp_path/'appdata').rglob('checkpoint.json'))
    with pytest.raises(ValueError, match='незавершённый'):
        recipe.read_recipe(track)


def test_negative_control_cannot_hide_a_missing_or_changed_full_frame(tmp_path, small_fingerprint):
    trajectory.record_trajectory(ballistic(), tmp_path/'source', 25.25, packet_steps=2)
    folder = tmp_path/'source'
    manifest = json.loads((folder/'manifest.json').read_bytes())
    frame = folder/manifest['frames'][1]['file']
    state = json.loads(frame.read_bytes())
    state['bodies'][0]['velocity'][0] += 1.
    frame.write_text(json.dumps(state), encoding='utf-8')
    manifest['frames'][1]['sha256'] = recipe.file_sha(frame)
    (folder/'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    payload = json.loads((folder/'recipe.json').read_bytes())['payload']
    payload['recording'] = manifest
    payload['manifest_sha256'] = recipe.file_sha(folder/'manifest.json')
    reseal(folder/'recipe.json', payload)
    result = recipe.replay_trajectory(folder, tmp_path/'repeat')
    assert not result['reproduced_prefix'] and result['mismatched_frames'] == [1]
    assert (tmp_path/'repeat/replay-report.json').exists()
    assert len(trajectory.Trajectory(tmp_path/'repeat').times) == 3


def test_truncated_replay_is_not_accepted_by_zip_prefix_comparison(tmp_path, monkeypatch, small_fingerprint):
    trajectory.record_trajectory(ballistic(), tmp_path/'source', 25.25, packet_steps=2)
    record = trajectory.record_trajectory
    def shortened(*args, **kwargs):
        kwargs['stop_requested'] = lambda: True
        return record(*args, **kwargs)
    monkeypatch.setattr(trajectory, 'record_trajectory', shortened)
    result = recipe.replay_trajectory(tmp_path/'source', tmp_path/'repeat')
    assert not result['reproduced_prefix'] and result['mismatched_frames'] == [1, 2]


def test_cli_audit_and_mismatch_exit_codes(tmp_path, small_fingerprint, capsys):
    from solar_simulator.commands import main
    trajectory.record_trajectory(ballistic(), tmp_path/'source', 25.25, packet_steps=2)
    assert main(['check-recipe', str(tmp_path/'source')]) == 0
    assert json.loads(capsys.readouterr().out)['compatible']
    path = tmp_path/'source/recipe.json'
    payload = json.loads(path.read_bytes())['payload']
    payload['fingerprint_start']['dependencies'] = {'changed': '1.0'}
    payload['fingerprint_end']['dependencies'] = {'changed': '1.0'}
    reseal(path, payload)
    assert main(['check-recipe', str(tmp_path/'source')]) == 1
    assert json.loads(capsys.readouterr().out)['differences'] == ['dependencies']
    with pytest.raises(SystemExit) as error:
        main(['replay-trajectory', str(tmp_path/'source'), str(tmp_path/'repeat')])
    assert error.value.code == 2 and not (tmp_path/'repeat').exists()


def test_nested_or_existing_destination_never_overwrites_a_recording(tmp_path, small_fingerprint):
    trajectory.record_trajectory(ballistic(), tmp_path/'source', 25.25, packet_steps=2)
    with pytest.raises(ValueError, match='вне исходной'):
        recipe.replay_trajectory(tmp_path/'source', tmp_path/'source/repeat')
    (tmp_path/'existing').mkdir()
    (tmp_path/'existing/keep.txt').write_bytes(b'user file')
    with pytest.raises(FileExistsError):
        recipe.replay_trajectory(tmp_path/'source', tmp_path/'existing')
    assert (tmp_path/'existing/keep.txt').read_bytes() == b'user file'


@pytest.mark.parametrize('case', ['strict', 'rotation', 'initial-contact', 'merge'])
def test_full_model_state_and_membership_are_repeated(tmp_path, small_fingerprint, case):
    if case == 'strict':
        from solar_simulator.solar_profiles import solar_sandbox
        state = solar_sandbox(profile='strict')
        target = 7200.
    elif case == 'rotation':
        from solar_simulator.application_profiles import lunar_rotation
        state = lunar_rotation()
        target = state.settings.dt*2.25
    else:
        radius = 1.
        distance = 1. if case == 'initial-contact' else 5.
        state = create_experiment([Body('left', 1., Vector3(-distance, 0., 0.), Vector3(1., 0., 0.), radius),
                                   Body('right', 1., Vector3(distance, 0., 0.), Vector3(-1., 0., 0.), radius)],
                                  Settings(3., contact_mode='stop' if case == 'initial-contact' else 'merge'))
        target = 10.25
    trajectory.record_trajectory(state, tmp_path/'source', target, packet_steps=2)
    result = recipe.replay_trajectory(tmp_path/'source', tmp_path/'repeat')
    assert result['reproduced_prefix']
    assert result['source_samples'] == result['replay_samples']


@pytest.mark.parametrize('backend,integrator', [('python', 'dop853'), ('rust', 'verlet')])
def test_real_recipe_replays_in_fresh_process_with_analytic_positions(tmp_path, backend, integrator):
    state = ballistic(integrator, backend)
    branch = branch_experiment(state)
    trajectory.record_trajectory(branch.child, tmp_path/'source', 25.25, packet_steps=2,
                                 parent_snapshot=branch.parent_snapshot)
    raw = (tmp_path/'source/recipe.json').read_text(encoding='utf-8')
    assert str(tmp_path) not in raw and str(Path.home()) not in raw and 'C:\\\\' not in raw
    environment = os.environ.copy()
    environment['LOCALAPPDATA'] = str(tmp_path/'appdata')
    result = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-m', 'solar_simulator', 'replay-trajectory',
                             str(tmp_path/'source'), str(tmp_path/'repeat')], capture_output=True, text=True,
                            encoding='utf-8', env=environment, timeout=60)
    assert result.returncode == 0, result.stdout+result.stderr
    assert json.loads(result.stdout)['reproduced_prefix']
    repeated = trajectory.Trajectory(tmp_path/'repeat')
    for index, time in enumerate(repeated.times):
        state, parent = repeated.frame(index)
        assert parent == branch.parent_snapshot
        actual = state.bodies[0].position
        assert (actual.x, actual.y, actual.z) == pytest.approx((3+2*time, 4-time, 5+.5*time), abs=1e-10, rel=0.)


def test_changed_source_tree_is_rejected_in_a_fresh_process(tmp_path):
    import shutil
    import solar_simulator
    trajectory.record_trajectory(ballistic(), tmp_path/'source', 25.25, packet_steps=2)
    tree = tmp_path/'different source'
    shutil.copytree(Path(solar_simulator.__file__).parent, tree/'solar_simulator',
                    ignore=shutil.ignore_patterns('__pycache__'))
    code = tree/'solar_simulator/input_units.py'
    with code.open('a', encoding='utf-8') as stream:
        stream.write('\n# Deliberate provenance negative control.\n')
    environment = os.environ.copy()
    environment['PYTHONPATH'] = str(tree)
    environment['LOCALAPPDATA'] = str(tmp_path/'appdata')
    result = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-m', 'solar_simulator', 'replay-trajectory',
                             str(tmp_path/'source'), str(tmp_path/'repeat')], cwd=tmp_path, env=environment,
                            capture_output=True, text=True, encoding='utf-8', timeout=60)
    assert result.returncode == 2 and 'package_files' in result.stderr
    assert not (tmp_path/'repeat').exists()
