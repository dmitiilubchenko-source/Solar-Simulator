"""Strict research-only canonical checkpoint, distinct from Experiment v schema.

Raw x/p/S/q, initial state, fixed coordinate contract and solver controls.
No normalisation, reboost, legacy migration or physical JPL certification.
"""
from dataclasses import dataclass, replace
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np
from scipy.integrate import DOP853, solve_ivp

from scripts.canonical_initial import SIUnits, finite_array, kinematics
from scripts.nbody_pn_spin import Parameters as PointParameters
from scripts.rigid_pn_model import Parameters, fields, validate_initial, rhs
from solar_simulator.nbody_rotation import RotationDOP853
from solar_simulator.rotation import RigidFigure


KIND = 'solar-simulator-research-canonical-checkpoint'
MODEL = 'finite-adm-1pn-lo-so-newton-one-rigid-q2-v1'
CORE_SOURCES = ('scripts/canonical_checkpoint.py', 'scripts/canonical_initial.py',
    'scripts/rigid_pn_model.py', 'scripts/nbody_pn_spin.py',
    'src/solar_simulator/rotation.py', 'src/solar_simulator/nbody_rotation.py',
    'src/solar_simulator/_numbers.py', 'src/solar_simulator/simulation.py',
    'src/solar_simulator/vector3.py', 'src/solar_simulator/coordinates.py')
RUNNING_ROOT = Path(__file__).resolve().parents[1]
LOADED_CORE_SHA = {p: hashlib.sha256((RUNNING_ROOT/p).read_bytes()).hexdigest() for p in CORE_SOURCES}


def canonical_text(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise ValueError('Finite JSON values required') from error


def exact_keys(value, expected, name):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f'{name}: expected exactly {sorted(expected)}')


def positive_number(value, name, *, zero=False):
    if (type(value) not in (int, float) or not math.isfinite(value)
            or (value < 0 if zero else value <= 0)):
        raise ValueError(f'{name}: finite {"nonnegative" if zero else "positive"} number required')


def numeric_array(value, shape, name):
    raw = np.asarray(value, dtype=object)
    if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, (int, float, np.integer, np.floating))
           for v in raw.ravel()):
        raise ValueError(f'{name}: numeric components, not strings or booleans, required')
    return finite_array(value, shape, name)


def validate_metadata(metadata, state_size):
    exact_keys(metadata, ['frame', 'units', 'integration', 'provenance'], 'metadata')
    frame = metadata['frame']
    exact_keys(frame, ['name', 'centre', 'spin_basis', 'time_coordinate', 'epoch_jd', 'evolution'], 'frame')
    if (type(frame['name']) is not str or not frame['name'].strip()
            or frame['centre'] != 'canonical-ADM-centres'
            or frame['spin_basis'] != 'finite-H-spatial-Euclidean'
            or frame['evolution'] != 'fixed-no-reboost'):
        raise ValueError('Explicit fixed canonical frame/basis required')
    if frame['time_coordinate'] == 'model-coordinate-time':
        if frame['epoch_jd'] is not None:
            raise ValueError('Synthetic model time has no Julian epoch')
    elif frame['time_coordinate'] == 'TDB-as-input-coordinate-time':
        positive_number(frame['epoch_jd'], 'epoch_jd')
    else:
        raise ValueError('Unsupported coordinate-time contract')
    units = metadata['units']
    if type(units) is not dict:
        raise ValueError('Explicit units required')
    if units.get('kind') == 'synthetic-G1':
        exact_keys(units, ['kind'], 'units')
        if frame['time_coordinate'] != 'model-coordinate-time':
            raise ValueError('Synthetic units require synthetic time')
    elif units.get('kind') == 'SI-similarity':
        exact_keys(units, ['kind', 'mass_kg', 'length_m', 'gravitational_constant'], 'units')
        SIUnits(units['mass_kg'], units['length_m'], units['gravitational_constant'])
    else:
        raise ValueError('Unknown unit contract')
    control = metadata['integration']
    exact_keys(control, ['method', 'rtol', 'atol', 'max_step'], 'integration')
    if control['method'] != 'canonical-per-block-DOP853':
        raise ValueError('Unsupported research solver contract')
    positive_number(control['rtol'], 'rtol'); positive_number(control['max_step'], 'max_step')
    if not 3e-14 <= control['rtol'] <= 1e-2:
        raise ValueError('rtol outside float64 research range')
    atol = numeric_array(control['atol'], (state_size,), 'atol')
    if np.any(atol <= 0):
        raise ValueError('Every state component needs positive atol')
    provenance = metadata['provenance']
    exact_keys(provenance, ['interpretation', 'physical_mapping_certified', 'sources'], 'provenance')
    if (type(provenance['interpretation']) is not str or not provenance['interpretation'].strip()
            or provenance['physical_mapping_certified'] is not False
            or type(provenance['sources']) is not list or not provenance['sources']):
        raise ValueError('Research mapping remains uncertified; explicit source records required')
    paths = []
    for source in provenance['sources']:
        exact_keys(source, ['path', 'sha256'], 'source')
        if (type(source['path']) is not str or not source['path'].strip()
                or type(source['sha256']) is not str or not re.fullmatch('[0-9a-f]{64}', source['sha256'])):
            raise ValueError('Nonempty source path and lowercase SHA256 required')
        paths.append(source['path'])
    if len(set(paths)) != len(paths):
        raise ValueError('Duplicate source records')
    canonical_text(metadata)


@dataclass(frozen=True)
class CanonicalCheckpoint:
    parameters: Parameters
    initial: tuple
    state: tuple
    time: float
    metadata_json: str

    def __post_init__(self):
        if not isinstance(self.parameters, Parameters):
            raise ValueError('Explicit finite-H parameters required')
        size = 9*len(self.parameters.orbital.masses)+4
        initial = validate_initial(numeric_array(self.initial, (size,), 'initial'), self.parameters)
        state = fields(numeric_array(self.state, (size,), 'state'), self.parameters)[0]
        if abs(np.linalg.norm(state[-4:])-1) > 1e-9:
            raise ValueError('Checkpoint raw quaternion norm outside research tolerance')
        positive_number(self.time, 'elapsed model time', zero=True)
        if (self.time == 0 and not np.array_equal(initial.view(np.uint64), state.view(np.uint64))):
            raise ValueError('At t=0 current state must equal initial bitwise')
        metadata = parse_json(self.metadata_json)
        validate_metadata(metadata, len(state))
        object.__setattr__(self, 'initial', tuple(map(float, initial)))
        object.__setattr__(self, 'state', tuple(map(float, state)))
        object.__setattr__(self, 'time', float(self.time))
        object.__setattr__(self, 'metadata_json', canonical_text(metadata))

    @property
    def metadata(self):
        return parse_json(self.metadata_json)  # Detached mutable copy.


def state_document(state, count):
    b = np.array(state[:-4]).reshape(3, count, 3)
    return dict(positions=b[0].tolist(), momenta=b[1].tolist(), spins=b[2].tolist(),
                quaternion=list(state[-4:]))


def to_document(checkpoint):
    p = checkpoint.parameters; count = len(p.orbital.masses)
    payload = dict(kind=KIND, schema=1, model=MODEL,
        parameters=dict(masses=list(map(float, p.orbital.masses)), c=float(p.orbital.c),
            figure_index=p.index, figure=dict(mass=float(p.figure.mass), moments=list(p.figure.moments),
                                            bounding_radius=float(p.figure.bounding_radius))),
        initial=state_document(checkpoint.initial, count), state=state_document(checkpoint.state, count),
        elapsed_model_time=checkpoint.time, metadata=checkpoint.metadata)
    payload['payload_sha256'] = hashlib.sha256(canonical_text(payload).encode('utf-8')).hexdigest()
    return payload


def from_document(document):
    exact_keys(document, ['kind', 'schema', 'model', 'parameters', 'initial', 'state',
                          'elapsed_model_time', 'metadata', 'payload_sha256'], 'canonical document')
    if document['kind'] != KIND or type(document['schema']) is not int or document['schema'] != 1 or document['model'] != MODEL:
        raise ValueError('Unsupported research schema/model; legacy velocity states cannot migrate here')
    payload = {k: v for k, v in document.items() if k != 'payload_sha256'}
    if document['payload_sha256'] != hashlib.sha256(canonical_text(payload).encode('utf-8')).hexdigest():
        raise ValueError('Canonical payload SHA256 mismatch')
    p = document['parameters']; exact_keys(p, ['masses', 'c', 'figure_index', 'figure'], 'parameters')
    f = p['figure']; exact_keys(f, ['mass', 'moments', 'bounding_radius'], 'figure')
    if type(p['masses']) is not list or type(f['moments']) is not list:
        raise ValueError('Mass and inertia lists required')
    for value in p['masses']+f['moments']+[f['mass'], f['bounding_radius'], p['c']]:
        positive_number(value, 'mass/inertia/radius/c')
    params = Parameters(PointParameters(tuple(p['masses']), p['c']),
        RigidFigure(f['mass'], tuple(f['moments']), f['bounding_radius']), p['figure_index'])
    count = len(params.orbital.masses)
    def unpack(b):
        exact_keys(b, ['positions', 'momenta', 'spins', 'quaternion'], 'canonical state')
        arrays = [numeric_array(b[k], (count, 3), k) for k in ['positions', 'momenta', 'spins']]
        return tuple(np.r_[np.stack(arrays).ravel(), numeric_array(b['quaternion'], (4,), 'quaternion')])
    return CanonicalCheckpoint(params, unpack(document['initial']), unpack(document['state']),
        document['elapsed_model_time'], canonical_text(document['metadata']))


def parse_json(text):
    def pairs(items):
        value = {}
        for key, item in items:
            if key in value:
                raise ValueError(f'Duplicate JSON key: {key}')
            value[key] = item
        return value
    def nonfinite(value):
        raise ValueError(f'Nonfinite JSON constant: {value}')
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError('Invalid canonical JSON') from error


def save(path, checkpoint):
    """Exclusive creation preserves existing checkpoints; UTF8 finite JSON."""
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(to_document(checkpoint), ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def load(path):
    return from_document(parse_json(Path(path).read_text(encoding='utf-8')))


def velocity_export(checkpoint):
    """Diagnostic dx_canonical/dt, NOT reimportable legacy/harmonic velocity."""
    v, w = kinematics(checkpoint.state, checkpoint.parameters)
    result = dict(kind='research-canonical-velocity-export', model=MODEL,
        definition='dx_canonical/dt; not harmonic velocity', elapsed_model_time=checkpoint.time,
        velocity_model_units=v.tolist(), attitude_rate_model_units=w.tolist(),
        checkpoint_payload_sha256=to_document(checkpoint)['payload_sha256'], metadata=checkpoint.metadata)
    units = checkpoint.metadata['units']
    if units['kind'] == 'SI-similarity':
        scale = SIUnits(units['mass_kg'], units['length_m'], units['gravitational_constant'])
        result['velocity_m_s'] = (v*scale.velocity_m_s).tolist()
        result['attitude_rate_per_s'] = (w/scale.time_s).tolist()
    return result


class CanonicalDOP853(RotationDOP853):
    """Reuse checked worst-block 5(3) norm for 9N+4 x/p/S/q layout."""
    def __init__(self, fun, t0, y0, t_bound, *, body_count, **kwargs):
        if type(body_count) is not int or body_count < 2 or np.size(y0) != 9*body_count+4:
            raise ValueError('Canonical layout requires 9N+4, N>=2')
        self.blocks = [slice(k, k+3) for k in range(0, 9*body_count, 3)]
        self.blocks += [slice(9*body_count, 9*body_count+4)]
        DOP853.__init__(self, fun, t0, y0, t_bound, **kwargs)


def verify_sources(checkpoint, root):
    """Require current model/solver hashes; declared sources stay within root."""
    root = Path(root).resolve()
    records = checkpoint.metadata['provenance']['sources']
    by_path = {r['path']: r['sha256'] for r in records}
    if not set(CORE_SOURCES) <= set(by_path):
        raise ValueError('Required canonical model/solver source hashes missing')
    for name, expected in by_path.items():
        path = (root/name).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError(f'Unavailable/outside-root checkpoint source: {name}')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f'Checkpoint source SHA256 mismatch: {name}')


def evolve(checkpoint, times, *, source_root):
    """Continue in the saved fixed frame; verify sources before AND after."""
    if Path(source_root).resolve() != RUNNING_ROOT:
        raise ValueError('Continuation must verify the source tree of the running modules')
    declared = {r['path']: r['sha256'] for r in checkpoint.metadata['provenance']['sources']}
    if any(declared.get(p) != h for p, h in LOADED_CORE_SHA.items()):
        raise ValueError('Checkpoint differs from loaded canonical source versions')
    grid = np.asarray(times, dtype=float)
    if (grid.ndim != 1 or len(grid) < 2 or not np.all(np.isfinite(grid))
            or np.any(np.diff(grid) <= 0) or grid[0] != checkpoint.time):
        raise ValueError('Increasing finite grid must start at exact checkpoint time')
    verify_sources(checkpoint, source_root)
    count = len(checkpoint.parameters.orbital.masses)
    control = checkpoint.metadata['integration']
    result = solve_ivp(lambda t, y: rhs(t, y, checkpoint.parameters),
        (float(grid[0]), float(grid[-1])), np.array(checkpoint.state), t_eval=grid,
        method=CanonicalDOP853, body_count=count, rtol=control['rtol'],
        atol=np.array(control['atol']), max_step=control['max_step'])
    if (not result.success or result.y.shape != (len(checkpoint.state), len(grid))
            or not np.array_equal(result.t, grid) or not np.all(np.isfinite(result.y))):
        raise ValueError('Failed/incomplete canonical integration')
    verify_sources(checkpoint, source_root)
    end = replace(checkpoint, state=tuple(result.y[:, -1]), time=float(grid[-1]))
    return end, result.y.T
