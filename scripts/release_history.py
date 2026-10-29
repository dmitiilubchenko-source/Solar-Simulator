"""Explicit 0.3.0 evidence mapping; historical replay never certifies the current product."""
import hashlib
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from zipfile import ZipFile

MANIFEST = 'scripts/validation/release032-history.json'
MANIFEST_SHA = '4139358c23b68219216f43a402d2c6aaa449abac52b78e8e19db97cb47c9c4f0'
ARCHIVE = 'scripts/validation/release030-sources.zip'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def evidence_path(root,name):
    """Resolve an internal recorded path on either OS without changing its bytes."""
    if not isinstance(name,str):raise ValueError('Expected internal evidence path')
    win=PureWindowsPath(name);relative=PurePosixPath(name.replace('\\','/'))
    if not name or win.drive or win.root or relative.is_absolute() or '..' in relative.parts:
        raise ValueError('Evidence path escapes checkout: '+name)
    root=Path(root).resolve();source=root.joinpath(*relative.parts).resolve()
    if not source.is_relative_to(root):raise ValueError('Evidence path escapes checkout: '+name)
    return source


def historical_sha(root, name, expected, *, cargo=False):
    """Allow only the recorded release transition, rejecting arbitrary live edits."""
    root = Path(root).resolve()
    path = (root/name).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Historical source escapes checkout')
    normalize = lambda data: data.replace(b'\r\n', b'\n') if cargo else data
    actual = digest(normalize(path.read_bytes())) if cargo else ui_historical_sha(root,name,expected)
    if actual == expected:
        return actual
    raw = (root/MANIFEST).read_bytes()
    if digest(raw) != MANIFEST_SHA:
        raise ValueError('Changed release history manifest')
    manifest = json.loads(raw)
    row = manifest['files'].get(name)
    if (manifest['schema'] != 1 or manifest['archive'] != ARCHIVE or row is None
            or row['canonical_cargo'] is not cargo or row['old_sha256'] != expected
            or (actual if cargo else ui_historical_sha(root,name,row['current_sha256'])) != row['current_sha256']):
        raise ValueError('Changed historical source or Cargo content: '+name)
    archive = root/ARCHIVE
    if digest(archive.read_bytes()) != manifest['archive_sha256']:
        raise ValueError('Changed historical source archive')
    with ZipFile(archive) as saved:
        historical = digest(normalize(saved.read(name)))
    if historical != expected:
        raise ValueError('Historical source SHA differs: '+name)
    return historical


def historical_cargo_hashes(root, expected):
    return {name:historical_sha(root, name, sha, cargo=True)
            for name, sha in expected.items()}


UI_ARCHIVE = 'scripts/validation/release032-ui-sources.zip'
UI_ARCHIVE_SHA = '1e78f034414bf6ddeacd7b19c2151eedb60a0816fff407a228e3a343310aa10f'
UI_FILES = ('src/solar_simulator/app.py', 'src/solar_simulator/comparison.py',
    'src/solar_simulator/comparison_view.py', 'src/solar_simulator/trajectory_loader.py',
    'scripts/release_history.py', 'scripts/replay_ias15_full_state.py',
    'scripts/replay_ias15_full_suite.py', 'scripts/replay_ias15_process.py',
    'scripts/replay_ias15_restart.py', 'scripts/replay_ias15_restart_step.py',
    'scripts/replay_ias15_session.py', 'tests/test_ias15_session_replay.py')

NUMERIC_ARCHIVE = 'scripts/validation/numeric-before373.zip'
NUMERIC_ARCHIVE_SHA = '0cbe5a3754c7732ac645d03c9a582b1193b9ec64475b6138974eff9fd2758abb'
NUMERIC_FILES = ('src/solar_simulator/vector3.py', 'src/solar_simulator/simulation.py',
    'src/solar_simulator/rotation.py', 'src/solar_simulator/nbody_rotation.py',
    'src/solar_simulator/experiment.py', 'src/solar_simulator/rust_backend.py',
    'src/solar_simulator/scenarios.py', 'src/solar_simulator/contacts.py',
    'src/solar_simulator/storage.py',
    'src/solar_simulator/impacts.py', 'src/solar_simulator/collisions.py',
    'scripts/release_history.py', 'scripts/assess_nominal_jpl.py', 'scripts/fixed_j2_year.py')

INSPECTION_ARCHIVE = 'scripts/validation/inspection-before377.zip'
INSPECTION_ARCHIVE_SHA = 'b744a773848c458326eb6ad58b13571b6da2862a0c0c9611e0e6ceb25bbc01bf'
INSPECTION_FILES = ('src/solar_simulator/commands.py', 'scripts/release_history.py',
                    'scripts/assess_runtime_reliability376.py')

ROTATION_ARCHIVE = 'scripts/validation/rotation-before380.zip'
ROTATION_ARCHIVE_SHA = '222461071aed44c49fcf72a573db52d9e29fbfd94d5da7f0fe749eb080b26147'
ROTATION_FILES = ('src/solar_simulator/nbody_rotation.py','src/solar_simulator/experiment.py',
    'src/solar_simulator/storage.py','src/solar_simulator/cli.py','src/solar_simulator/inspection.py',
    'src/solar_simulator/convergence.py','scripts/release_history.py','tests/test_sandbox_acceptance.py')

LABORATORY_ARCHIVE = 'scripts/validation/laboratory-before381.zip'
LABORATORY_ARCHIVE_SHA = 'b840ba94506142266f71eb8b6fa62825eb94a28bc754ac941978afd6d80f14a3'
LABORATORY_FILES = ('src/solar_simulator/app.py','src/solar_simulator/application_profiles.py',
    'scripts/release_history.py','tests/test_sandbox_acceptance.py')

CI_ARCHIVE = 'scripts/validation/ci-before382.zip'
CI_ARCHIVE_SHA = 'a2b6a165f1c333a903fd7be4c5a3d2da2e8bf92b95ca9de7f24e1e065f89d078'
CI_FILES = ('scripts/release_history.py','scripts/sandbox_checks/accept_sandbox.py',
    'scripts/assess_two_q2_380.py','tests/test_runtime_step379_evidence.py',
    'tests/test_current_runtime_qualification.py','tests/test_sandbox_acceptance.py')


def ui_historical_sha(root,name,expected):
    """Exact historical evidence only; never authorize a live worker."""
    root=Path(root).resolve();path=(root/name).resolve()
    if Path(name).is_absolute() or not path.is_relative_to(root):
        raise ValueError('Historical source escapes checkout')
    actual=digest(path.read_bytes()) if path.is_file() else None
    if actual==expected:return actual
    from io import BytesIO
    for archive_name, archive_sha, names in (
            (CI_ARCHIVE, CI_ARCHIVE_SHA, CI_FILES),
            (LABORATORY_ARCHIVE, LABORATORY_ARCHIVE_SHA, LABORATORY_FILES),
            (ROTATION_ARCHIVE, ROTATION_ARCHIVE_SHA, ROTATION_FILES),
            (INSPECTION_ARCHIVE, INSPECTION_ARCHIVE_SHA, INSPECTION_FILES),
            (HISTORY_ARCHIVE, HISTORY_ARCHIVE_SHA, HISTORY_FILES),
            (NUMERIC_ARCHIVE, NUMERIC_ARCHIVE_SHA, NUMERIC_FILES),
            (UI_ARCHIVE, UI_ARCHIVE_SHA, UI_FILES)):
        if name not in names:continue
        path=root/archive_name
        if not path.is_file():continue
        raw=path.read_bytes()
        if digest(raw)!=archive_sha:raise ValueError('Changed historical source archive')
        with ZipFile(BytesIO(raw)) as archive:
            old=digest(archive.read(name))
        if old==expected:return old
    return actual


# Exact pre374 bytes; old receipts and their recorded SHA are never rewritten.
HISTORY_ARCHIVE = 'scripts/validation/history-before374.zip'
HISTORY_ARCHIVE_SHA = '9d55542c89dcb741264adea38f6b060821833edfcbcb4531ca4aa66d1455b7fd'
HISTORY_FILES = ('scripts/assess_nominal_jpl.py',
 'scripts/assess_relative_canonical_checkpoint.py',
 'scripts/assess_rotation_time.py',
 'scripts/canonical_checkpoint.py',
 'scripts/newton_year_cache.py',
 'scripts/release_history.py',
 'scripts/replay_ias15_session.py',
 'scripts/replay_native_newton_year.py',
 'tests/test_canonical_checkpoint.py',
 'tests/test_canonical_solar.py',
 'tests/test_ias15_native_newton_replay.py',
 'tests/test_ias15_native_session_replay.py',
 'tests/test_ias15_restart_replay.py',
 'tests/test_ias15_restart_step_replay.py',
 'tests/test_ias15_session_replay.py',
 'tests/test_lunar_initial_boundary.py',
 'tests/test_native_newton_year.py',
 'tests/test_native_newton_year_replay.py',
 'tests/test_relative_canonical_checkpoint_audit.py',
 'tests/test_release_history.py',
 'tests/test_release_ui_history.py',
 'tests/test_rotation_time_audit.py',
 'tests/test_sandbox_demo.py',
 'tests/test_sandbox_models.py',
 'tests/test_time_control.py')
HISTORICAL_FILES = set(UI_FILES) | set(NUMERIC_FILES) | set(HISTORY_FILES) | set(INSPECTION_FILES) | set(ROTATION_FILES) | set(LABORATORY_FILES) | set(CI_FILES)
HISTORICAL_ARCHIVES = (UI_ARCHIVE, NUMERIC_ARCHIVE, HISTORY_ARCHIVE, INSPECTION_ARCHIVE, ROTATION_ARCHIVE, LABORATORY_ARCHIVE, CI_ARCHIVE)


def verify_checkpoint_history(checkpoint, root):
    """Check declared historical bytes only. Never authorize evolve/conversion.

    Old records predate today's dependency closure; this proves their declared
    provenance, not the complete old environment or current numerical fitness.
    """
    required = {'scripts/canonical_checkpoint.py', 'scripts/canonical_initial.py',
        'scripts/rigid_pn_model.py', 'scripts/nbody_pn_spin.py',
        'src/solar_simulator/rotation.py', 'src/solar_simulator/nbody_rotation.py'}
    if hasattr(checkpoint, 'pair'):
        required |= {'scripts/relative_canonical.py', 'scripts/relative_canonical_checkpoint.py'}
    records = {s['path']:s['sha256'] for s in checkpoint.metadata['provenance']['sources']}
    if not required <= records.keys():
        raise ValueError('Required historical checkpoint source hashes missing')
    for name, expected in records.items():
        if ui_historical_sha(root, name, expected) != expected:
            raise ValueError('Historical checkpoint source SHA256 mismatch: '+name)
