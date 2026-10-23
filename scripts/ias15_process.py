"""Small trusted process wire/launcher. Optional science imports are lazy."""
import base64
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import subprocess
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
BASE = 'docs/ias15-full-suite-validation.json'
SAMPLES = 'docs/ias15-full-suite-samples.npz'
POINTS = ('first', 'midpoint')
SOURCE_NAMES = ('docs/ias15-process-protocol.md', 'scripts/ias15_process.py',
                'scripts/ias15_process_worker.py', 'scripts/assess_ias15_process.py',
                'scripts/replay_ias15_process.py', 'tests/test_ias15_process.py')
KEYS = {'schema', 'case', 'epsilon', 'point', 'index', 'time', 'origin', 'abi', 'version',
        'library_sha', 'digest', 'physical_sha', 'identities', 'masses', 'parent_pid',
        'launch_id', 'source_sha256', 'input_sha256'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON key: '+key)
        result[key] = value
    return result


def read_request(path, expected_sha):
    raw = Path(path).read_bytes()
    if len(raw) > 100_000 or sha(raw) != expected_sha:
        raise ValueError('Request size/SHA mismatch')
    request = json.loads(raw, object_pairs_hook=unique)
    if (set(request) != KEYS or request['schema'] != 'ias15-process-request-v1'
            or request['point'] not in POINTS or request['epsilon'] not in ('1e-09', '1e-11')
            or type(request['parent_pid']) is not int or request['parent_pid'] <= 0
            or type(request['index']) is not int or request['index'] <= 0
            or type(request['time']) is not float or not math.isfinite(request['time']) or request['time'] <= 0
            or not isinstance(request['masses'], list) or len(request['masses']) != 2
            or not all(type(m) is float and math.isfinite(m) and m > 0 for m in request['masses'])
            or not isinstance(request['launch_id'], str) or not request['launch_id']):
        raise ValueError('Invalid process request schema')
    for key in ('source_sha256', 'input_sha256'):
        if not isinstance(request[key], dict) or not request[key]:
            raise ValueError('Missing file bindings')
    return request


def verify_files(mapping, root=ROOT):
    root = Path(root).resolve()
    for name, digest in mapping.items():
        path = (root/name).resolve()
        if not path.is_relative_to(root) or Path(name).is_absolute():
            raise ValueError('File binding outside project')
        if sha(path.read_bytes()) != digest:
            raise ValueError('File binding SHA mismatch: '+name)


def select(ends, point):
    import numpy as np
    if point not in POINTS:
        raise ValueError('Undeclared restore point')
    index = 1 if point == 'first' else int(np.searchsorted(ends, ends[-1]/2))
    if not 0 < index < len(ends)-1:
        raise ValueError('Restore point needs a nonempty continuation')
    return index


def bindings():
    base = json.loads((ROOT/BASE).read_bytes())
    sources = base['source_sha256'] | {n: sha((ROOT/n).read_bytes()) for n in SOURCE_NAMES}
    inputs = base['input_sha256'] | {BASE: sha((ROOT/BASE).read_bytes()), SAMPLES: base['array_archive_sha256']}
    return sources, inputs


def context(name, epsilon):
    import numpy as np
    from scripts.ias15_full_state import FullSnapshot
    base = json.loads((ROOT/BASE).read_bytes())
    if not base['complete'] or not base['aggregate']['full_state_gate_passed'] or name not in base['results']:
        raise ValueError('Unqualified frozen full-state source')
    prefix = name+'__'+epsilon+'__'
    with np.load(ROOT/SAMPLES, allow_pickle=False) as data:
        ends = data[prefix+'packet_endpoints'].copy()
        states = data[prefix+'packet_states'].copy()
        binaries = data[prefix+'full_binary_base64'].copy()
        physicals = data[prefix+'full_physical_json'].copy()
        times, warm = data[name+'__times'].copy(), data[prefix+'warm'].copy()
    def saved(index):
        raw, text = base64.b64decode(str(binaries[index]), validate=True), str(physicals[index])
        return FullSnapshot(raw, sha(raw), text, sha(text.encode()), base['origins'][name], '5.2.2',
            base['results'][name][epsilon]['abi'],
            sha(json.dumps(base['library_files_sha256'], sort_keys=True).encode()), ('body[0]', 'body[1]'))
    return dict(name=name, epsilon=epsilon, base=base, ends=ends, states=states,
                times=times, warm=warm, saved=saved, request=base['requests'][name])


def request_for(ctx, point, parent_pid, launch_id, sources, inputs):
    index = select(ctx['ends'], point)
    saved = ctx['saved'](index)
    return dict(schema='ias15-process-request-v1', case=ctx['name'], epsilon=ctx['epsilon'], point=point,
        index=index, time=float(ctx['ends'][index]), origin=saved.origin, abi=saved.abi, version=saved.version,
        library_sha=saved.library_sha, digest=saved.digest, physical_sha=saved.physical_sha,
        identities=list(saved.identities), masses=ctx['request']['masses'], parent_pid=parent_pid,
        launch_id=launch_id, source_sha256=sources, input_sha256=inputs)


def validate_context(request, ctx):
    expected = request_for(ctx, request['point'], request['parent_pid'], request['launch_id'],
                           request['source_sha256'], request['input_sha256'])
    if request != expected:
        raise ValueError('Request differs from frozen snapshot metadata')


def signature(saved):
    from scripts.ias15_full_state import numeric_fields, parse, PREFIX, SCALARS, BUFFERS
    header, _ = parse(saved.binary)
    fields = numeric_fields(saved)
    if {k for k in fields if k.startswith(PREFIX)} != {PREFIX+k for k in SCALARS+BUFFERS}:
        raise ValueError('Expected all17IAS15 payloads')
    digest = hashlib.sha256(header)
    for name, value in sorted(fields.items()):
        encoded = name.encode('ascii')
        digest.update(struct.pack('>QQ', len(encoded), len(value))+encoded+value)
    return digest.hexdigest()


def persist(directory, index, saved, reference):
    """Write candidate first; a committed marker requires exact field equality."""
    from dataclasses import asdict
    from scripts.ias15_full_state import numeric_fields
    stem = Path(directory)/str(index).zfill(4)
    metadata = asdict(saved)
    del metadata['binary']
    with stem.with_suffix('.bin').open('xb') as target:
        target.write(saved.binary)
    with stem.with_suffix('.json').open('x', encoding='utf-8') as target:
        json.dump(metadata, target, allow_nan=False)
    if numeric_fields(saved) != numeric_fields(reference):
        raise ArithmeticError('Continued fields differ at packet '+str(index))
    with stem.with_suffix('.committed').open('x', encoding='ascii') as target:
        target.write(saved.digest+'\n')


def launch(command, directory, timeout=55., launch_id=None):
    """Preserve all logs on nonzero/timeout; never use a shell or visible window."""
    directory = Path(directory)
    started = perf_counter()
    with (directory/'stdout.log').open('xb') as stdout, (directory/'stderr.log').open('xb') as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr,
            stdin=subprocess.PIPE if launch_id is not None else subprocess.DEVNULL,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0)
        if launch_id is not None:
            metadata = dict(supervisor_pid=os.getpid(), launched_pid=process.pid, launch_id=launch_id)
            try:
                process.stdin.write((json.dumps(metadata)+'\n').encode())
                process.stdin.close()
            except BrokenPipeError:
                pass  # A failed child still has exit status and immutable logs.
        timed_out = False
        try:
            code = process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.kill()
            code = process.wait(timeout=5.)
    return dict(pid=process.pid, returncode=code, timed_out=timed_out, wall_seconds=perf_counter()-started)


def validate_identity(row, request, launched):
    supervisor, actual_launch = request['parent_pid'], launched['pid']
    direct = row['pid'] == actual_launch and row['ppid'] == supervisor
    wrapper = (row['os_name'] == 'nt' and row['ppid'] == actual_launch
               and row['pid'] not in (actual_launch, supervisor) and actual_launch != supervisor)
    if (not (direct or wrapper) or row['supervisor_pid'] != supervisor
            or row['launched_pid'] != actual_launch or row['launch_id'] != request['launch_id']):
        raise ValueError('Wrong supervisor/launcher/worker identity chain')


def validate_child(row, request, request_sha, launched):
    validate_identity(row, request, launched)
    if (not row['complete']
            or row['request_sha256'] != request_sha or row['rebound_already_imported']
            or row['restore_masks'] != [0, 0] or not row['c_restore_started']
            or launched['returncode'] != 0 or launched['timed_out']):
        raise ValueError('Child process identity, lifecycle or restore failure')
