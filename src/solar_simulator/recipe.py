"""Installation fingerprints and a bound recipe; no force/integration formulas.

Hashes describe files, not loaded-code attestation or a hermetic OS image.
Never install dependencies or run code supplied by a recipe.
"""
import hashlib
import json
from importlib import import_module, metadata
from importlib.machinery import EXTENSION_SUFFIXES, ExtensionFileLoader
import os
from pathlib import Path, PurePosixPath
import platform
import struct
import sys
import sysconfig

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from .sandbox import _canonical
from .storage import _read_document, _write_document


def file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _version(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def _dependencies():
    pending = ['numpy', 'scipy', 'matplotlib']
    found = {}
    while pending:
        name = canonicalize_name(pending.pop())
        if name in found:
            continue
        try:
            distribution = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            found[name] = dict(version=None, files={}, inventory_complete=False)
            continue
        files = {}
        for entry in sorted(distribution.files or (), key=str):
            relative = PurePosixPath(str(entry).replace('\\', '/'))
            if (relative.is_absolute() or '..' in relative.parts or ':' in str(relative)
                    or relative.suffix not in ('.py', '.pyd', '.dll', '.so')):
                continue
            files[str(relative)] = file_sha(distribution.locate_file(entry))
        direct_url = distribution.read_text('direct_url.json')
        editable = bool(json.loads(direct_url).get('dir_info', {}).get('editable', False)) if direct_url else False
        found[name] = dict(version=distribution.version, files=files,
                           inventory_complete=bool(files) and not editable)
        for text in distribution.requires or ():
            requirement = Requirement(text)
            if requirement.marker is None or requirement.marker.evaluate({'extra': ''}):
                pending.append(requirement.name)
    return {name: found[name] for name in sorted(found)}


def _native(backend):
    if backend != 'rust':
        return None
    wrapper = import_module('solar_native')
    compiled = getattr(wrapper, 'solar_native', wrapper)
    path = Path(compiled.__file__)
    if (not any(str(path).endswith(suffix) for suffix in EXTENSION_SUFFIXES)
            or not isinstance(compiled.__spec__.loader, ExtensionFileLoader)):
        raise RuntimeError('Для Rust требуется настоящий compiled solar_native')
    files = {path.name: file_sha(path)}
    if wrapper is not compiled:
        files['__init__.py'] = file_sha(wrapper.__file__)
    return dict(version=_version('solar-native'), files=files)


def runtime_fingerprint(backend):
    """Fresh content hashes, no mtime cache or private installation paths."""
    package = Path(__file__).resolve().parent
    files = {path.relative_to(package).as_posix(): file_sha(path)
             for path in sorted(package.rglob('*')) if path.is_file()
             and path.suffix in ('.py', '.json', '.txt') and '__pycache__' not in path.parts}
    library = sysconfig.get_config_var('LDLIBRARY')
    libpath = Path(sys.base_prefix)/library if library else None
    if libpath is not None and not libpath.is_file():
        libpath = Path(sysconfig.get_config_var('LIBDIR') or sys.base_prefix)/library
    numerical_environment = {}
    for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS', 'PYTHONHASHSEED'):
        value = os.environ.get(key)
        if value is not None and not value.isdecimal() and not (key == 'PYTHONHASHSEED' and value == 'random'):
            raise ValueError('Нечисловая настройка окружения: '+key)
        numerical_environment[key] = value
    return dict(application_version=_version('solar-simulator'), package_files=files,
                dependencies=_dependencies(), native=_native(backend),
                python=dict(version=platform.python_version(), implementation=sys.implementation.name,
                            cache_tag=sys.implementation.cache_tag, soabi=sysconfig.get_config_var('SOABI'),
                            free_threaded_build=bool(sysconfig.get_config_var('Py_GIL_DISABLED')),
                            optimize=sys.flags.optimize, pointer_bits=struct.calcsize('P')*8,
                            byteorder=sys.byteorder,
                            executable_sha256=file_sha(getattr(sys, '_base_executable', sys.executable)),
                            shared_library_sha256=file_sha(libpath) if libpath and libpath.is_file() else None),
                platform=dict(system=platform.system(), release=platform.release(), machine=platform.machine()),
                numerical_environment=numerical_environment)


def write_recipe(directory, manifest, start, end):
    directory = Path(directory)
    frames = manifest['frames']
    payload = dict(format='solar-recording-recipe', schema_version=1,
                   fingerprint_start=start, fingerprint_end=end, stable=end is not None and start == end,
                   recording=manifest, packet_boundaries_seconds=[
                       [first['time_seconds'], second['time_seconds']] for first, second in zip(frames, frames[1:])],
                   manifest_sha256=file_sha(directory/'manifest.json') if frames else None)
    _write_document(dict(payload=payload, sha256=hashlib.sha256(_canonical(payload).encode('utf-8')).hexdigest()),
                    directory/'recipe.json')


def read_recipe(trajectory):
    path = trajectory.directory/'recipe.json'
    if not path.is_file():
        raise ValueError('У записи нет recipe.json; происхождение старой записи не подтверждено')
    document = _read_document(path)
    if type(document) is not dict or set(document) != {'payload', 'sha256'}:
        raise ValueError('Неверная оболочка recipe')
    payload = document['payload']
    keys = {'format', 'schema_version', 'fingerprint_start', 'fingerprint_end', 'stable',
            'recording', 'packet_boundaries_seconds', 'manifest_sha256'}
    if (type(payload) is not dict or set(payload) != keys or payload['format'] != 'solar-recording-recipe'
            or type(payload['schema_version']) is not int or payload['schema_version'] != 1
            or type(payload['stable']) is not bool or type(payload['fingerprint_start']) is not dict
            or type(payload['fingerprint_end']) is not dict
            or payload['stable'] != (payload['fingerprint_start'] == payload['fingerprint_end'])
            or hashlib.sha256(_canonical(payload).encode('utf-8')).hexdigest() != document['sha256']):
        raise ValueError('Повреждённый или незавершённый recipe')
    expected = trajectory.metadata
    boundaries = [[first, second] for first, second in zip(trajectory.times, trajectory.times[1:])]
    if (_canonical(payload['recording']) != _canonical(expected)
            or _canonical(payload['packet_boundaries_seconds']) != _canonical(boundaries)
            or payload['manifest_sha256'] != file_sha(trajectory.directory/'manifest.json')):
        raise ValueError('Recipe не соответствует manifest/эпохам/пакетам записи')
    return payload


def audit_recipe(trajectory):
    payload = read_recipe(trajectory)
    state, _ = trajectory.frame(0)
    current = runtime_fingerprint(state.settings.backend)
    differences = sorted(key for key in current.keys() | payload['fingerprint_start'].keys()
                         if current.get(key) != payload['fingerprint_start'].get(key))
    if not payload['stable']:
        differences.insert(0, 'recording-environment-changed')
    unverified = sorted(name for name, item in current.get('dependencies', {}).items()
                        if not item.get('inventory_complete', False))
    if unverified:
        differences.append('dependency-inventory-unverified')
    return dict(compatible=not differences, differences=differences, samples=len(trajectory.times),
                stable=payload['stable'], unverified_dependencies=unverified, physical_accuracy_claim=False)


def replay_trajectory(source, destination):
    """Recompute the published prefix with original global target and batch.

    A failed/stopped source prefix is not promoted to a completed target.
    Mismatches retain the new recording and yield an explicit negative report.
    """
    from .trajectory import Trajectory, record_trajectory
    source = Trajectory(source)
    destination = Path(destination).resolve()
    if destination.is_relative_to(source.directory):
        raise ValueError('Повтор нужно сохранять вне исходной записи')
    audit = audit_recipe(source)
    if not audit['compatible']:
        raise ValueError('Окружение/код несовместимы с recipe: '+', '.join(audit['differences']))
    expected = read_recipe(source)
    calls = 0
    packets = len(source.times)-1
    def stop():
        nonlocal calls
        if calls >= packets:
            return True
        calls += 1
        return False
    state, parent = source.frame(0)
    metadata = source.metadata
    record_trajectory(state, destination, metadata['requested_target_seconds'],
                      packet_steps=metadata['packet_steps'], parent_snapshot=parent, stop_requested=stop)
    actual = Trajectory(destination)
    actual_recipe = read_recipe(actual)
    original_frames, repeated_frames = metadata['frames'], actual.metadata['frames']
    mismatches = [i for i in range(max(len(original_frames), len(repeated_frames)))
                  if i >= len(original_frames) or i >= len(repeated_frames)
                  or original_frames[i] != repeated_frames[i]]
    environment_matches = (actual_recipe['stable'] and
                           actual_recipe['fingerprint_start'] == expected['fingerprint_start'])
    report = dict(format='solar-replay-report', schema_version=1,
                  reproduced_prefix=not mismatches and environment_matches,
                  mismatched_frames=mismatches, environment_matches=environment_matches,
                  source_samples=len(original_frames), replay_samples=len(repeated_frames),
                  source_status=metadata['status'], replay_status=actual.metadata['status'],
                  requested_target_seconds=metadata['requested_target_seconds'],
                  last_committed_time_seconds=actual.times[-1], physical_accuracy_claim=False)
    _write_document(report, destination/'replay-report.json')
    return report
