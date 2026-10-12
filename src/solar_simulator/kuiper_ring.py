"""Explicit own discrete ring approximation, sharing the normal body/force model.

The six pinned initial snapshots allow phase and point-count comparisons. Ring
points interact with every body, including one another; no masked EIH terms,
future trajectories, source interpolation or forced circular paths are used.
"""
import hashlib
from importlib.resources import files
import json

from .perturbers import (SupplementSpec, SUPPLEMENTS, KUIPER_DATASET_SHA256,
    KUIPER_GM_SHA256, extend_system)

MANIFEST_SHA256='b0959e9f5e24931899c0031ed642e09f63082874d3b577afc042431a05088461'


def specifications():
    raw=files('solar_simulator.data').joinpath('kuiper-ring-manifest.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_SHA256:
        raise ValueError('Изменён закреплённый набор аппроксимаций кольца Койпера')
    result={}
    for variant in json.loads(raw)['variants']:
        payload=files('solar_simulator.data').joinpath(variant['filename']).read_bytes()
        if hashlib.sha256(payload).hexdigest()!=variant['dataset_sha256']:
            raise ValueError('Изменено начальное состояние дискретного кольца')
        identities=tuple((b['id'],b['name']) for b in json.loads(payload)['bodies'])
        spec=SupplementSpec(variant['filename'],variant['dataset_sha256'],variant['gm_sha256'],
            KUIPER_DATASET_SHA256,KUIPER_GM_SHA256,variant['sources_sha256'],identities)
        result[variant['points'],variant['phase_index']]=spec
    return result


RING_SPECS=specifications()
# The shared provenance registry handles figure inheritance and checkpoint load.
SUPPLEMENTS.update((spec.dataset_sha256,spec) for spec in RING_SPECS.values())


def solar_system_ring(points=36,phase_index=0):
    """384 unchanged bodies plus an autonomous ring; not exact DE441 geometry."""
    if type(points) is not int or type(phase_index) is not int or (points,phase_index) not in RING_SPECS:
        raise ValueError('Нужно 36/72/144 точек кольца и номер фазы 0/1')
    return extend_system(RING_SPECS[points,phase_index])
