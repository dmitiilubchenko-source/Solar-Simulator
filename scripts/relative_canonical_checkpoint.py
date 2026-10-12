"""Strict research Jacobi checkpoint; never alias Cartesian or velocity states.

Raw mixed coordinate/momentum slots, spatial S and q, fixed pair/order/frame.
Geometry validation uses the local pair anchor, never an absolute export.
"""
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path
import json

import numpy as np
from scipy.integrate import solve_ivp

from scripts.canonical_checkpoint import (CanonicalCheckpoint, CanonicalDOP853,
    MODEL, CORE_SOURCES as CARTESIAN_SOURCES, RUNNING_ROOT, canonical_text,
    exact_keys, positive_number, numeric_array, validate_metadata, parse_json,
    verify_sources as verify_cartesian_sources)
from scripts.canonical_initial import SIUnits, kinematics
from scripts.nbody_pn_spin import Parameters as PointParameters
from scripts.rigid_pn_model import Parameters, fields, validate_initial
from scripts.relative_canonical import Pair, from_cartesian, to_cartesian, rhs
from solar_simulator.rotation import RigidFigure


KIND = 'solar-simulator-research-relative-canonical-checkpoint'
REPRESENTATION = 'mass-weighted-pair-Jacobi-X-r-P-pr-spatial-S-quaternion'
CORE_SOURCES = CARTESIAN_SOURCES+('scripts/relative_canonical.py',
                                'scripts/relative_canonical_checkpoint.py')
LOADED_CORE_SHA = {p:hashlib.sha256((RUNNING_ROOT/p).read_bytes()).hexdigest() for p in CORE_SOURCES}


@dataclass(frozen=True)
class RelativeCheckpoint:
    parameters: Parameters
    pair: Pair
    body_names: tuple
    initial: tuple
    state: tuple
    time: float
    metadata_json: str

    def __post_init__(self):
        if (not isinstance(self.parameters, Parameters) or not isinstance(self.pair, Pair)
                or self.pair.masses != self.parameters.orbital.masses):
            raise ValueError('Explicit matching finite-H parameters and Jacobi pair required')
        count = len(self.pair.masses); size = 9*count+4
        if (type(self.body_names) is not tuple or len(self.body_names) != count
                or any(type(n) is not str or not n.strip() for n in self.body_names)
                or len(set(self.body_names)) != count):
            raise ValueError('Unique ordered body names required')
        initial = numeric_array(self.initial,(size,),'relative initial')
        state = numeric_array(self.state,(size,),'relative current')
        validate_initial(to_cartesian(initial,self.pair,anchored=True),self.parameters)
        fields(to_cartesian(state,self.pair,anchored=True),self.parameters)
        if abs(np.linalg.norm(state[-4:])-1) > 1e-9:
            raise ValueError('Raw quaternion outside checkpoint tolerance')
        positive_number(self.time,'elapsed model time',zero=True)
        if self.time == 0 and not np.array_equal(initial.view(np.uint64),state.view(np.uint64)):
            raise ValueError('At t=0 relative state must equal initial bitwise')
        metadata = parse_json(self.metadata_json); validate_metadata(metadata,size)
        object.__setattr__(self,'initial',tuple(map(float,initial)))
        object.__setattr__(self,'state',tuple(map(float,state)))
        object.__setattr__(self,'time',float(self.time))
        object.__setattr__(self,'metadata_json',canonical_text(metadata))

    @property
    def metadata(self):
        return parse_json(self.metadata_json)


def state_document(state, count):
    b = np.asarray(state[:-4]).reshape(3,count,3)
    return dict(coordinate_slots=b[0].tolist(),momentum_slots=b[1].tolist(),
                spatial_spins=b[2].tolist(),quaternion=list(state[-4:]))


def to_document(checkpoint):
    if not isinstance(checkpoint,RelativeCheckpoint):
        raise ValueError('RelativeCheckpoint required; no implicit Cartesian migration')
    p = checkpoint.parameters; count = len(checkpoint.pair.masses)
    payload = dict(kind=KIND,schema=1,model=MODEL,
        representation=dict(kind=REPRESENTATION,pair_indices=[checkpoint.pair.first,checkpoint.pair.second]),
        body_names=list(checkpoint.body_names),
        parameters=dict(masses=list(p.orbital.masses),c=p.orbital.c,figure_index=p.index,
            figure=dict(mass=p.figure.mass,moments=list(p.figure.moments),bounding_radius=p.figure.bounding_radius)),
        initial=state_document(checkpoint.initial,count),state=state_document(checkpoint.state,count),
        elapsed_model_time=checkpoint.time,metadata=checkpoint.metadata)
    payload['payload_sha256'] = hashlib.sha256(canonical_text(payload).encode('utf-8')).hexdigest()
    return payload


def from_document(document):
    exact_keys(document,['kind','schema','model','representation','body_names','parameters',
                         'initial','state','elapsed_model_time','metadata','payload_sha256'],'relative document')
    if document['kind'] != KIND or type(document['schema']) is not int or document['schema'] != 1 or document['model'] != MODEL:
        raise ValueError('Unsupported relative schema/model; other representations cannot migrate here')
    payload = {k:v for k,v in document.items() if k!='payload_sha256'}
    if document['payload_sha256'] != hashlib.sha256(canonical_text(payload).encode('utf-8')).hexdigest():
        raise ValueError('Relative payload SHA256 mismatch')
    representation = document['representation']; exact_keys(representation,['kind','pair_indices'],'representation')
    indices = representation['pair_indices']
    if representation['kind'] != REPRESENTATION or type(indices) is not list or len(indices)!=2:
        raise ValueError('Explicit supported Jacobi pair representation required')
    p = document['parameters']; exact_keys(p,['masses','c','figure_index','figure'],'parameters')
    f = p['figure']; exact_keys(f,['mass','moments','bounding_radius'],'figure')
    if type(p['masses']) is not list or type(f['moments']) is not list or type(document['body_names']) is not list:
        raise ValueError('Explicit masses/inertia/ordered names lists required')
    for v in p['masses']+f['moments']+[p['c'],f['mass'],f['bounding_radius']]:positive_number(v,'parameter')
    params = Parameters(PointParameters(tuple(p['masses']),p['c']),
        RigidFigure(f['mass'],tuple(f['moments']),f['bounding_radius']),p['figure_index'])
    pair = Pair(tuple(p['masses']),*indices); count = len(pair.masses)
    def unpack(value):
        exact_keys(value,['coordinate_slots','momentum_slots','spatial_spins','quaternion'],'relative state')
        blocks = [numeric_array(value[k],(count,3),k) for k in ['coordinate_slots','momentum_slots','spatial_spins']]
        return tuple(np.r_[np.stack(blocks).ravel(),numeric_array(value['quaternion'],(4,),'quaternion')])
    return RelativeCheckpoint(params,pair,tuple(document['body_names']),unpack(document['initial']),
        unpack(document['state']),document['elapsed_model_time'],canonical_text(document['metadata']))


def save(path, checkpoint):
    document = to_document(checkpoint)
    with Path(path).open('x',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(document,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def load(path):
    return from_document(parse_json(Path(path).read_text(encoding='utf-8')))


def from_cartesian_checkpoint(checkpoint, pair, body_names, *, integration):
    """Explicit coordinate conversion, requiring caller-declared new controls.

    Does not certify physical ADM/SSC mapping or recover lost input bits.
    The raw S/q, epoch, units and original provenance are retained.
    """
    if (not isinstance(checkpoint,CanonicalCheckpoint) or not isinstance(pair,Pair)
            or type(body_names) not in (tuple,list)):
        raise ValueError('Explicit Cartesian canonical checkpoint and pair required')
    if pair.masses != checkpoint.parameters.orbital.masses:
        raise ValueError('Conversion pair masses differ')
    verify_cartesian_sources(checkpoint,RUNNING_ROOT)
    meta = checkpoint.metadata; meta['integration'] = parse_json(canonical_text(integration))
    sources = {s['path']:s['sha256'] for s in meta['provenance']['sources']}
    for path,expected in LOADED_CORE_SHA.items():
        if path in sources and sources[path]!=expected:
            raise ValueError('Conversion differs from loaded model source versions')
        if path not in sources:meta['provenance']['sources'].append(dict(path=path,sha256=expected))
    meta['provenance']['interpretation'] += '; explicit mass-weighted Jacobi pair coordinate conversion, not physical migration'
    result = RelativeCheckpoint(checkpoint.parameters,pair,tuple(body_names),
        tuple(from_cartesian(checkpoint.initial,pair)),tuple(from_cartesian(checkpoint.state,pair)),
        checkpoint.time,canonical_text(meta))
    verify_sources(result,RUNNING_ROOT)
    return result


def verify_sources(checkpoint, root):
    if not isinstance(checkpoint,RelativeCheckpoint):raise ValueError('RelativeCheckpoint required')
    declared = {s['path']:s['sha256'] for s in checkpoint.metadata['provenance']['sources']}
    if not set(CORE_SOURCES)<=set(declared):raise ValueError('Required relative source hashes missing')
    verify_cartesian_sources(checkpoint,root)


def evolve(checkpoint, times, *, source_root):
    """Continue raw relative state in its fixed frame, validating saved sources."""
    if not isinstance(checkpoint,RelativeCheckpoint):raise ValueError('RelativeCheckpoint required')
    if Path(source_root).resolve()!=RUNNING_ROOT:
        raise ValueError('Must verify source tree of running modules')
    declared = {s['path']:s['sha256'] for s in checkpoint.metadata['provenance']['sources']}
    if any(declared.get(p)!=h for p,h in LOADED_CORE_SHA.items()):
        raise ValueError('Checkpoint differs from loaded relative source versions')
    raw_grid = np.asarray(times,dtype=object)
    if raw_grid.ndim!=1:raise ValueError('One-dimensional time grid required')
    grid = numeric_array(times,raw_grid.shape,'time grid')
    if len(grid)<2 or np.any(np.diff(grid)<=0) or grid[0]!=checkpoint.time:
        raise ValueError('Increasing grid must start at exact checkpoint time')
    verify_sources(checkpoint,source_root); control = checkpoint.metadata['integration']
    result = solve_ivp(lambda t,y:rhs(t,y,checkpoint.parameters,checkpoint.pair),
        (float(grid[0]),float(grid[-1])),np.array(checkpoint.state),t_eval=grid,
        method=CanonicalDOP853,body_count=len(checkpoint.pair.masses),rtol=control['rtol'],
        atol=np.array(control['atol']),max_step=control['max_step'])
    if (not result.success or result.y.shape!=(len(checkpoint.state),len(grid))
            or not np.array_equal(result.t,grid) or not np.all(np.isfinite(result.y))):
        raise ValueError('Failed/incomplete relative canonical integration')
    verify_sources(checkpoint,source_root)
    return replace(checkpoint,state=tuple(result.y[:,-1]),time=float(grid[-1])),result.y.T


def velocity_export(checkpoint):
    """Diagnostic derivatives of canonical centres; preserve direct relative v."""
    if not isinstance(checkpoint,RelativeCheckpoint):raise ValueError('RelativeCheckpoint required')
    v,w = kinematics(to_cartesian(checkpoint.state,checkpoint.pair,anchored=True),checkpoint.parameters)
    pair_flow = rhs(checkpoint.time,checkpoint.state,checkpoint.parameters,checkpoint.pair)
    relative = pair_flow[:3*len(checkpoint.pair.masses)].reshape(-1,3)[checkpoint.pair.second]
    out = dict(kind='research-relative-canonical-velocity-export',definition='canonical centre dx/dt, not harmonic velocity',
        elapsed_model_time=checkpoint.time,body_names=list(checkpoint.body_names),
        pair_indices=[checkpoint.pair.first,checkpoint.pair.second],velocity_model_units=v.tolist(),
        relative_velocity_model_units=relative.tolist(),attitude_rate_model_units=w.tolist(),
        checkpoint_payload_sha256=to_document(checkpoint)['payload_sha256'],metadata=checkpoint.metadata)
    units = checkpoint.metadata['units']
    if units['kind']=='SI-similarity':
        scale = SIUnits(**{k:v for k,v in units.items() if k!='kind'})
        out.update(velocity_m_s=(v*scale.velocity_m_s).tolist(),
            relative_velocity_m_s=(relative*scale.velocity_m_s).tolist(),attitude_rate_per_s=(w/scale.time_s).tolist())
    return out
