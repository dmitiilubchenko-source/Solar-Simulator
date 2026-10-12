"""Pinned SB441 year for all 343 asteroids; developer data, no runtime change.

The initial catalogue uses the existing DE441 Sun vector and common frame.
All former 27 bodies are retained verbatim when constructing a trial system.
Future Chebyshev records below are for source validation and force screening.
"""
from dataclasses import asdict
import argparse
import hashlib
import json
from math import isfinite
from pathlib import Path
import struct
import subprocess

import numpy as np
from solar_simulator.perturbers import solar_system_asteroids_full
from solar_simulator.simulation import Body, G
from solar_simulator.vector3 import Vector3

if __package__:
    from .audit_perturbers import (CATALOG_SHA, MANIFEST_SHA, SOURCE_DIR,
        pinned_json, source_blocks, decode_inventory, validate_catalog)
    from .fetch_asteroid_data import ALL_IDENTITIES, heliocentric_state
    from .fetch_figure_profile import HEADER_SHA, decode_header
    from .fetch_pluto_data import rotation
else:
    from audit_perturbers import (CATALOG_SHA, MANIFEST_SHA, SOURCE_DIR,
        pinned_json, source_blocks, decode_inventory, validate_catalog)
    from fetch_asteroid_data import ALL_IDENTITIES, heliocentric_state
    from fetch_figure_profile import HEADER_SHA, decode_header
    from fetch_pluto_data import rotation

YEAR_MANIFEST_SHA = '4a4427da7d5ff55fabf8a67b4a3e0aa913fe32f3207bc304bd8d13477891148a'
INITIAL_SHA = '50434ff910366e319c9447ede9c7da59fcdac543746cd9840570d3cd05d809b0'


def inputs():
    catalog = pinned_json('de441-perturber-catalog.json', CATALOG_SHA)
    metadata = pinned_json('sb441-catalog-ranges.json', MANIFEST_SHA)
    manifest = pinned_json('sb441-343-ranges.json', YEAR_MANIFEST_SHA)
    if (manifest['catalog_sha256'] != CATALOG_SHA or manifest['metadata_sha256'] != MANIFEST_SHA
            or manifest['url'] != metadata['url'] or manifest['total_bytes'] != metadata['total_bytes']
            or manifest['epoch_jd_tdb'] != 2461321.5 or manifest['duration_seconds'] != 31557600):
        raise ValueError('Asteroid catalogue provenance mismatch')
    segments, _ = decode_inventory(metadata, source_blocks(metadata), manifest['epoch_jd_tdb'], manifest['duration_seconds'])
    raw = (SOURCE_DIR / 'validation/de441-header.441').read_bytes()
    if hashlib.sha256(raw).hexdigest() != HEADER_SHA:
        raise ValueError('DE441 constants changed')
    constants = decode_header(raw)
    validate_catalog(constants, catalog, segments)
    return catalog, manifest, segments, constants


def year_blocks(manifest, *, download=False):
    packed = (SOURCE_DIR / 'validation/sb441-343-year.bin').read_bytes()
    expected_length = sum(e['byte_range'][1]-e['byte_range'][0]+1 for e in manifest['entries'])
    if len(packed) != expected_length:
        raise ValueError('Truncated/extra year coefficients')
    cache = Path('.tools/sb441-343')
    if download:
        cache.mkdir(parents=True, exist_ok=True)
    result = {}
    offset = 0
    for entry in manifest['entries']:
        role = entry['role']
        first, last = entry['byte_range']
        if not 0 <= first <= last < manifest['total_bytes'] or role in result:
            raise ValueError('Invalid/duplicate coefficient range')
        length = last-first+1
        raw = packed[offset:offset+length]
        offset += length
        if download:
            path, headers = cache/(role+'.bin'), cache/(role+'.headers')
            subprocess.run(['curl.exe', '--fail', '--silent', '--show-error', '--proto', '=https',
                '--max-time', '45', '--max-filesize', str(length), '--range', f'{first}-{last}',
                '--dump-header', str(headers), '--output', str(path), manifest['url']], check=True)
            if f"bytes {first}-{last}/{manifest['total_bytes']}" not in headers.read_text():
                raise ValueError('SPK coefficient Content-Range mismatch')
            raw = path.read_bytes()
        if len(raw) != length or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError(f'SB441 coefficient hash mismatch: {role}')
        result[role] = raw
    return result


def decode_year(manifest, blocks, segments, identities):
    """Validate directory/record pointers, interval grid, degree and coverage."""
    first = (manifest['epoch_jd_tdb']-2451545)*86400
    last = first+manifest['duration_seconds']
    entries = {e['role']: e for e in manifest['entries']}
    expected_roles = {f'{kind}-{identity}' for identity in identities for kind in ('tail', 'records')}
    if set(entries) != expected_roles or set(blocks) != expected_roles or len(entries) != len(manifest['entries']):
        raise ValueError('Incomplete/extra asteroid record groups')
    records = {}
    for identity in identities:
        descriptor = segments[identity]
        a, z = descriptor['first_word'], descriptor['last_word']
        tail_key, records_key = f'tail-{identity}', f'records-{identity}'
        if len(blocks[tail_key]) != 32:
            raise ValueError('Truncated type-2 directory')
        init, interval, size, count = struct.unpack('<4d', blocks[tail_key])
        if (not all(isfinite(v) for v in (init, interval, size, count))
                or interval <= 0 or size != 26 or count != int(count) or count <= 0
                or a+int(size*count)+3 != z
                or entries[tail_key]['byte_range'] != [(z-4)*8, z*8-1]):
            raise ValueError('Invalid type-2 directory/address')
        low, high = int((first-init)//interval), int((last-init)//interval)
        if not 0 <= low <= high < count:
            raise ValueError('Asteroid record coverage')
        expected_range = [(a-1+low*int(size))*8, (a-1+(high+1)*int(size))*8-1]
        raw = blocks[records_key]
        if (entries[records_key]['byte_range'] != expected_range
                or len(raw) != (high-low+1)*int(size)*8):
            raise ValueError('Type-2 coefficient pointer/size mismatch')
        value = np.frombuffer(raw, dtype='<f8').reshape(high-low+1, int(size)).copy()
        centres = init+(np.arange(low, high+1)+.5)*interval
        if (not np.all(np.isfinite(value)) or not np.array_equal(value[:, 0], centres)
                or not np.all(value[:, 1] == interval/2)):
            raise ValueError('Invalid type-2 grid/coefficients')
        records[identity] = value
    return records


def initial_document(catalog, manifest, constants, records):
    initial, origin = solar_system_asteroids_full()
    sun = next(b for b in initial if b.name == 'Sun')
    sun_state = np.array([sun.position.x, sun.position.y, sun.position.z,
        sun.velocity.x, sun.velocity.y, sun.velocity.z])
    transform = rotation()
    scale = (constants['AU']*1000)**3/86400**2
    bodies = []
    differences = {}
    current = {identity: body for (identity, _, _), body in zip(ALL_IDENTITIES, initial[11:])}
    for row in catalog['bodies']:
        if row['group'] != 'asteroid':
            continue
        state = (heliocentric_state(records[row['id']], origin.epoch_jd_tdb).reshape(2, 3)@transform.T).ravel()+sun_state
        bodies.append(dict(id=row['id'], name=row['name'], gm_m3_s2=constants[row['constant']]*scale,
            position=state[:3].tolist(), velocity=state[3:].tolist()))
        if row['id'] in current:
            old = current[row['id']]
            old_state = np.array([old.position.x, old.position.y, old.position.z,
                old.velocity.x, old.velocity.y, old.velocity.z])
            delta = state-old_state
            differences[row['name']] = dict(position_metres=float(np.linalg.norm(delta[:3])),
                velocity_m_per_s=float(np.linalg.norm(delta[3:])))
    if any(v['position_metres'] > .01 or v['velocity_m_per_s'] > 1e-8 for v in differences.values()):
        raise RuntimeError('Existing SB441-N16 states differ from N373s')
    return dict(schema=1, base_origin=asdict(origin), epoch_jd_tdb=origin.epoch_jd_tdb,
        frame=origin.frame, center=origin.center, units='SI', vector_correction='NONE',
        catalog_sha256=CATALOG_SHA, header_sha256=HEADER_SHA, range_manifest_sha256=YEAR_MANIFEST_SHA,
        source_url=manifest['url'], bodies=bodies, existing_sixteen_crosscheck=differences,
        limitation='Developer initial catalogue. Trial systems retain all original 27 bodies verbatim and append only missing asteroids. Year coefficients are source validation, never a prescribed runtime trajectory.')


def trial_system(document, selected_ids=None):
    """Build developer trial bodies while preserving the entire current parent."""
    raw = (json.dumps(document, indent=2, allow_nan=False)+'\n').encode('utf-8')
    if hashlib.sha256(raw).hexdigest() != INITIAL_SHA:
        raise ValueError('Pinned trial initial catalogue changed')
    initial, origin = solar_system_asteroids_full()
    if (document['base_origin'] != asdict(origin) or document['epoch_jd_tdb'] != origin.epoch_jd_tdb
            or document['range_manifest_sha256'] != YEAR_MANIFEST_SHA):
        raise ValueError('Trial initial catalogue provenance')
    current = {identity for identity, _, _ in ALL_IDENTITIES}
    rows = {b['id']: b for b in document['bodies']}
    if len(rows) != 343 or not current <= rows.keys():
        raise ValueError('Trial catalogue identities')
    missing = set(rows)-current
    selected = missing if selected_ids is None else set(selected_ids)
    if (not selected <= missing or (selected_ids is not None and len(selected) != len(selected_ids))):
        raise ValueError('Trial selection must contain only missing asteroids')
    for row in document['bodies']:
        if row['id'] in selected:
            initial.append(Body(row['name'], row['gm_m3_s2']/G, Vector3(*row['position']), Vector3(*row['velocity'])))
    if len({b.name for b in initial}) != len(initial):
        raise ValueError('Trial duplicate names')
    return initial


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    catalog, manifest, segments, constants = inputs()
    identities = {b['id'] for b in catalog['bodies'] if b['group'] == 'asteroid'}
    records = decode_year(manifest, year_blocks(manifest, download=args.download), segments, identities)
    document = initial_document(catalog, manifest, constants, records)
    path = Path('docs/asteroids-343-initial.json')
    path.write_bytes((json.dumps(document, indent=2, allow_nan=False)+'\n').encode('utf-8'))
    print('initial sha256', hashlib.sha256(path.read_bytes()).hexdigest(), 'asteroids', len(document['bodies']))
    print('source bytes', sum(e['byte_range'][1]-e['byte_range'][0]+1 for e in manifest['entries']))


if __name__ == '__main__':
    main()
