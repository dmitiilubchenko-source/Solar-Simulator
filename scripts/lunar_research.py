"""Source-bound conditional lunar experiment using the unchanged finite H57.

Pinned harmonic x/v are assigned to conditional canonical centres. This API
binds initial receipt, parameters, pair and raw initial state through restart;
it does not authenticate a current trajectory or certify physical PN mapping.
"""
from dataclasses import dataclass, replace
import hashlib
from pathlib import Path

import numpy as np

from scripts.canonical_checkpoint import canonical_text, exact_keys, parse_json
from scripts.lunar_initial_boundary import PURPOSE
from scripts.lunar_initial_receipt import make_receipt, verify_receipt, CODE_SOURCES
from scripts.pinned_lunar_initial import source_inputs, from_pinned_dataset, array_digest
from scripts.relative_canonical import Pair, from_cartesian
from scripts import relative_canonical_checkpoint as relative


ROOT = Path(__file__).resolve().parents[1]
KIND = 'solar-simulator-source-bound-lunar-research'
SOURCES = tuple(sorted(set(CODE_SOURCES+relative.CORE_SOURCES+(
    'scripts/lunar_research.py', 'scripts/run_lunar_research.py',
    'src/solar_simulator/data/solar-system-moon-20261008.json',
    'src/solar_simulator/data/lunar-spin-solid-equivalent-20261008.json'))))
INTERPRETATION = ('conditional-research; pinned harmonic x/v assigned to canonical centres; '
    'global-TDB PA R/Rdot assigned to Euclidean canonical attitude; effective mean-solid I; '
    'no physical clock/basis/SSC/extended-body migration; Earth-Moon mass-weighted Jacobi pair')


def source_hashes():
    return {name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SOURCES}


LOADED_SOURCE_SHA = source_hashes()


def verify_running_sources():
    if source_hashes()!=LOADED_SOURCE_SHA:
        raise ValueError('Changed loaded lunar research sources')


def initial_parts(integration):
    verify_running_sources()
    args = source_inputs(); state, _ = from_pinned_dataset(purpose=PURPOSE)
    pair = Pair(args['parameters'].orbital.masses,3,4)
    initial = from_cartesian(state,pair)
    metadata = dict(frame=dict(name=args['frame'],centre='canonical-ADM-centres',
        spin_basis='finite-H-spatial-Euclidean',time_coordinate='TDB-as-input-coordinate-time',
        epoch_jd=args['epoch_jd_tdb'],evolution='fixed-no-reboost'),
        units=dict(kind='SI-similarity',**vars(args['units'])),
        integration=parse_json(canonical_text(integration)),
        provenance=dict(interpretation=INTERPRETATION,physical_mapping_certified=False,
            sources=[dict(path=k,sha256=v) for k,v in LOADED_SOURCE_SHA.items()]))
    verify_running_sources()
    return args, pair, initial, metadata


def default_controls():
    """Same SI-based tolerances as audits61-63, adapted to P/pr masses."""
    args = source_inputs(); state, _ = from_pinned_dataset(purpose=PURPOSE)
    count = len(args['body_names']); units = args['units']; masses = np.array(args['parameters'].orbital.masses)
    spin = np.full((count,3),1e-30)
    spin[4] = 1e-13*np.linalg.norm(state[:-4].reshape(3,count,3)[2,4])
    weights = masses.copy(); weights[3] = masses[3]+masses[4]
    weights[4] = masses[3]*masses[4]/weights[3]
    atol = np.r_[np.full(3*count,1e-4/units.length_m),
        np.repeat(weights*1e-10/units.velocity_m_s,3),spin.ravel(),np.full(4,1e-13)]
    return dict(method='canonical-per-block-DOP853',rtol=1e-11,atol=atol.tolist(),
        max_step=21600./units.time_s)


@dataclass(frozen=True)
class LunarResearch:
    receipt_json: str
    checkpoint: relative.RelativeCheckpoint

    def __post_init__(self):
        validate(self)
        object.__setattr__(self,'receipt_json',canonical_text(parse_json(self.receipt_json)))

    @property
    def receipt(self):
        return parse_json(self.receipt_json)


def validate(experiment):
    """Rebuild the initial boundary, retaining the evolving current state."""
    verify_running_sources()
    if not isinstance(experiment,LunarResearch) or not isinstance(experiment.checkpoint,relative.RelativeCheckpoint):
        raise ValueError('Source-bound LunarResearch and relative checkpoint required')
    verify_receipt(parse_json(experiment.receipt_json))
    cp = experiment.checkpoint
    args, pair, initial, metadata = initial_parts(cp.metadata['integration'])
    if (cp.parameters!=args['parameters'] or cp.pair!=pair or cp.body_names!=args['body_names']
            or not np.array_equal(np.array(cp.initial).view(np.uint64),initial.view(np.uint64))
            or cp.metadata_json!=canonical_text(metadata)):
        raise ValueError('Changed pinned lunar initial/parameters/pair/frame/units/provenance')
    relative.verify_sources(cp,ROOT)
    verify_running_sources()


def create(*,purpose,integration=None):
    receipt = make_receipt(purpose=purpose)
    control = default_controls() if integration is None else integration
    args, pair, initial, meta = initial_parts(control)
    cp = relative.RelativeCheckpoint(args['parameters'],pair,args['body_names'],
        tuple(initial),tuple(initial),0.,canonical_text(meta))
    return LunarResearch(canonical_text(receipt),cp)


def to_document(experiment):
    validate(experiment)
    payload = dict(kind=KIND,schema=1,initial_receipt=experiment.receipt,
        checkpoint=relative.to_document(experiment.checkpoint))
    return dict(payload,payload_sha256=hashlib.sha256(canonical_text(payload).encode('utf-8')).hexdigest())


def from_document(document):
    exact_keys(document,['kind','schema','initial_receipt','checkpoint','payload_sha256'],'lunar experiment')
    if document['kind']!=KIND or type(document['schema']) is not int or document['schema']!=1:
        raise ValueError('Unsupported source-bound lunar research kind/schema')
    payload = {k:v for k,v in document.items() if k!='payload_sha256'}
    if document['payload_sha256']!=hashlib.sha256(canonical_text(payload).encode('utf-8')).hexdigest():
        raise ValueError('Changed lunar experiment checksum')
    receipt = verify_receipt(document['initial_receipt'])
    return LunarResearch(canonical_text(receipt),relative.from_document(document['checkpoint']))


def save(path,experiment):
    text = canonical_text(to_document(experiment))+'\n'
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream: stream.write(text)


def load(path):
    return from_document(parse_json(Path(path).read_text(encoding='utf-8')))


def evolve(experiment,times):
    validate(experiment)
    end, states = relative.evolve(experiment.checkpoint,times,source_root=ROOT)
    return replace(experiment,checkpoint=end), states


def velocity_export(experiment):
    validate(experiment)
    out = relative.velocity_export(experiment.checkpoint)
    out.update(initial_receipt_sha256=experiment.receipt['payload_sha256'],
        source_bound_experiment_sha256=to_document(experiment)['payload_sha256'],
        state_sha256=array_digest(experiment.checkpoint.state),physical_mapping_certified=False)
    return out
