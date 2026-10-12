"""Strict source-bound initial receipt, not an integrator checkpoint.

Loading regenerates the pinned conditional input and compares its complete
contract/state fingerprint. Checksums detect changes, not authenticate authors.
"""
import hashlib
from pathlib import Path

import numpy as np
import scipy

from scripts.canonical_checkpoint import canonical_text,exact_keys,parse_json,CORE_SOURCES
from scripts.lunar_initial_boundary import PURPOSE
from scripts.pinned_lunar_initial import from_pinned_dataset,array_digest


ROOT = Path(__file__).resolve().parents[1]
KIND = 'solar-simulator-research-lunar-initial-receipt'
REPRESENTATION = 'canonical-x-p-spatial-S-raw-q'
CODE_SOURCES = CORE_SOURCES+('scripts/lunar_initial_boundary.py','scripts/pinned_lunar_initial.py',
    'scripts/lunar_initial_receipt.py','src/solar_simulator/relativity.py',
    'src/solar_simulator/simulation.py','src/solar_simulator/vector3.py','src/solar_simulator/spin_initial.py')


def code_hashes():
    return {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in CODE_SOURCES}


LOADED_CODE_SHA = code_hashes()


def payload_checksum(payload):
    return hashlib.sha256(canonical_text(payload).encode('utf-8')).hexdigest()


def expected_payload(purpose):
    if code_hashes()!=LOADED_CODE_SHA:raise ValueError('Changed loaded initial source code')
    state,info = from_pinned_dataset(purpose=purpose)
    if code_hashes()!=LOADED_CODE_SHA:raise ValueError('Changed source code during initialization')
    return dict(kind=KIND,schema=1,purpose=PURPOSE,representation=REPRESENTATION,
        state_sha256=array_digest(state),metadata=info,
        environment=dict(numpy=np.__version__,scipy=scipy.__version__,code_sha256=dict(LOADED_CODE_SHA)))


def make_receipt(*,purpose):
    payload = expected_payload(purpose)
    return dict(payload,payload_sha256=payload_checksum(payload))


def verify_receipt(document):
    """Reject structural/semantic changes even if the checksum was recomputed."""
    exact_keys(document,['kind','schema','purpose','representation','state_sha256',
        'metadata','environment','payload_sha256'],'lunar initial receipt')
    if type(document['kind']) is not str or document['kind']!=KIND:
        raise ValueError('Unsupported initial receipt kind')
    if type(document['schema']) is not int or document['schema']!=1:
        raise ValueError('Unsupported initial receipt schema')
    if type(document['purpose']) is not str or document['purpose']!=PURPOSE:
        raise ValueError('Physical mapping is not certified; conditional receipt required')
    if document['representation']!=REPRESENTATION:raise ValueError('Unsupported initial representation')
    payload = {k:v for k,v in document.items() if k!='payload_sha256'}
    if type(document['payload_sha256']) is not str or document['payload_sha256']!=payload_checksum(payload):
        raise ValueError('Changed initial receipt checksum')
    expected = expected_payload(PURPOSE)
    # Canonical JSON preserves distinctions False/0, int/float and signed zero.
    if canonical_text(payload)!=canonical_text(expected):
        raise ValueError('Changed initial source/state/contract/environment')
    return parse_json(canonical_text(document))


def save_receipt(path,document):
    verified = verify_receipt(document);text = canonical_text(verified)+'\n'
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:stream.write(text)


def load_receipt(path):
    return verify_receipt(parse_json(Path(path).read_text(encoding='utf-8')))
