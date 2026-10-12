"""Audit missing DE441 masses and source coverage; never change runtime physics.

Runs offline using checked-in source metadata. Use --download to recheck
16 KiB of SPK metadata, the DE441 header and source memorandum against JPL.
No future orbit is fitted.
"""
import argparse
import hashlib
import json
from math import fsum, isclose, isfinite
from pathlib import Path
import re
import struct
import subprocess

import numpy as np
from solar_simulator.perturbers import solar_system_asteroids_full
from solar_simulator.simulation import G

if __package__:
    from .fetch_asteroid_data import ALL_IDENTITIES
    from .fetch_ephemerides import fetch
    from .fetch_figure_profile import HEADER_SHA, HEADER_URL, decode_header
else:
    from fetch_asteroid_data import ALL_IDENTITIES
    from fetch_ephemerides import fetch
    from fetch_figure_profile import HEADER_SHA, HEADER_URL, decode_header

CATALOG_SHA = 'f922e96ec250222f7cf8915ecb7ff572f97490e868c5371ec40e6a05fd0fd586'
MANIFEST_SHA = 'aae65ca7f930a4de06a114088893afa2b5e2985215394cd9981a78b6425209f5'
PAPER_URL = 'https://ssd.jpl.nasa.gov/doc/Park.2021.AJ.DE440.pdf'
SOURCE_DIR = Path(__file__).resolve().parent


def pinned_json(filename, digest):
    raw = (SOURCE_DIR / filename).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError(f'Pinned source changed: {filename}')
    return json.loads(raw)


def source_blocks(manifest, download=False):
    cache = Path('.tools/sb441-catalog')
    if download:
        cache.mkdir(parents=True, exist_ok=True)
    blocks = {}
    packed = (SOURCE_DIR / 'validation/sb441-catalog-metadata.bin').read_bytes()
    if len(packed) != 1024*len(manifest['entries']):
        raise ValueError('Truncated/extra packed metadata')
    for index, entry in enumerate(manifest['entries']):
        role = entry['role']
        if not re.fullmatch(r'header|summary-\d+', role) or role in blocks:
            raise ValueError('Invalid/duplicate source role')
        first, last = entry['byte_range']
        if not 0 <= first <= last < manifest['total_bytes'] or last-first != 1023:
            raise ValueError('Invalid metadata range')
        path = cache / (role + '.bin')
        if download:
            headers = cache / (role + '.headers')
            subprocess.run(['curl.exe', '--fail', '--silent', '--show-error',
                '--proto', '=https', '--max-time', '45', '--max-filesize', '1024',
                '--range', f'{first}-{last}', '--dump-header', str(headers),
                '--output', str(path), manifest['url']], check=True)
            if f"bytes {first}-{last}/{manifest['total_bytes']}" not in headers.read_text():
                raise ValueError('SPK Content-Range mismatch')
        raw = path.read_bytes() if download else packed[index*1024:(index+1)*1024]
        if len(raw) != 1024 or hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError(f'Pinned SPK metadata changed: {role}')
        blocks[role] = raw
    return blocks


def decode_inventory(manifest, blocks, epoch, duration):
    """Read actual DAF linkage, validate word addresses and select year coverage."""
    if not isfinite(epoch) or not isfinite(duration) or duration <= 0:
        raise ValueError('Invalid inventory interval')
    header = blocks['header']
    if (len(header) != 1024 or header[:8] != b'DAF/SPK '
            or struct.unpack_from('<2i', header, 8) != (2, 6)
            or header[88:96] != b'LTL-IEEE'):
        raise ValueError('Unsupported DAF format')
    entries = {e['role']: e for e in manifest['entries']}
    if entries['header']['byte_range'] != [0, 1023]:
        raise ValueError('Header address mismatch')
    first_et = (epoch-2451545.) * 86400
    last_et = first_et + duration
    record, declared_last, free = struct.unpack_from('<3i', header, 76)
    previous = 0
    seen = set()
    selected = {}
    count = 0
    while record:
        if record in seen or record < 2:
            raise ValueError('Cyclic/invalid DAF chain')
        seen.add(record)
        role = f'summary-{record}'
        if role not in blocks or entries[role]['byte_range'] != [(record-1)*1024, record*1024-1]:
            raise ValueError('Missing/misaddressed DAF summary')
        block = blocks[role]
        if len(block) != 1024:
            raise ValueError('Truncated DAF summary')
        next_, prev, n = struct.unpack_from('<3d', block)
        if (not all(isfinite(v) and v == int(v) for v in (next_, prev, n))
                or prev != previous or next_ < 0 or not 0 <= n <= 25):
            raise ValueError('Invalid DAF summary links/count')
        for index in range(int(n)):
            start, end = struct.unpack_from('<2d', block, 24+index*40)
            identity, center, frame, kind, a, z = struct.unpack_from('<6i', block, 40+index*40)
            if (not isfinite(start) or not isfinite(end) or start >= end
                    or (center, frame, kind) != (10, 1, 2)
                    or not 1 <= a <= z < free or z*8 > manifest['total_bytes']):
                raise ValueError('Invalid/unsupported SPK segment')
            count += 1
            if start <= first_et and end >= last_et:
                if identity in selected:
                    raise ValueError('Ambiguous year coverage')
                selected[identity] = dict(id=identity, center=center, frame=frame,
                    type=kind, first_word=a, last_word=z, start_et=start, end_et=end)
        previous, record = record, int(next_)
    if previous != declared_last or set(blocks) != {'header'} | {f'summary-{r}' for r in seen}:
        raise ValueError('Incomplete DAF chain')
    return selected, count


def validate_catalog(constants, catalog, segments):
    """Check memo masses against all header MA entries and independent SPK IDs."""
    rows = catalog['bodies']
    identities = set()
    keys = set()
    for row in rows:
        identity, key, gm = row['id'], row['constant'], row['gm_au3_per_day2']
        if identity in identities or key in keys or key not in constants:
            raise ValueError('Duplicate/unknown catalog identity')
        if not isfinite(gm) or gm <= 0 or not isclose(gm, constants[key], rel_tol=1e-15, abs_tol=0.):
            raise ValueError('Memo/header GM mismatch')
        if row['group'] == 'asteroid':
            if key != f"MA{row['number']:04d}" or identity != 2000000+row['number']:
                raise ValueError('Asteroid identity mismatch')
        elif row['group'] == 'kuiper-belt-object':
            if not re.fullmatch(r'MA80\d\d', key):
                raise ValueError('KBO constant mismatch')
        else:
            raise ValueError('Unknown mass group')
        identities.add(identity)
        keys.add(key)
    asteroid_keys = {k for k in constants if re.fullmatch(r'MA\d{4}', k) and int(k[2:]) < 8000}
    kbo_keys = {f'MA80{i:02d}' for i in range(1, 31)}
    ring_keys = {f'MA82{i:02d}' for i in range(1, 37)}
    all_ma = {k for k in constants if re.fullmatch(r'MA\d{4}', k)}
    if (len(asteroid_keys) != 343 or keys != asteroid_keys | kbo_keys
            or all_ma != keys | ring_keys or set(segments) != identities
            or sum(r['group'] == 'asteroid' for r in rows) != 343):
        raise ValueError('Incomplete mass inventory')
    ring = [constants[k] for k in sorted(ring_keys)]
    if any(not isfinite(mu) or mu <= 0 or mu != ring[0] for mu in ring):
        raise ValueError('Expected 36 equal positive ring masses')
    return asteroid_keys, kbo_keys, ring_keys


def inner_ring_acceleration(position, radius, gm, points=72, phase=0.):
    """Diagnostic angular quadrature of a uniform ring, only deep inside it.

    Position is relative to the Sun in Ecliptic J2000. This is not a runtime
    force or the initial conditions of the 36 moving DE441 ring particles.
    """
    p = np.asarray(position, dtype=float)
    if (p.shape != (3,) or not np.all(np.isfinite(p)) or not isfinite(radius)
            or radius <= 0 or not isfinite(gm) or gm <= 0 or not isfinite(phase)
            or not isinstance(points, int) or points < 16 or np.linalg.norm(p) >= radius/10):
        raise ValueError('Ring diagnostic requires a finite inner point and positive parameters')
    angle = phase + np.arange(points) * (2*np.pi/points)
    ring = radius*np.column_stack((np.cos(angle), np.sin(angle), np.zeros(points)))
    d = ring-p
    terms = (gm/points)*d/np.linalg.norm(d, axis=1)[:, None]**3
    return np.array([fsum(terms[:, i]) for i in range(3)])


def audit(constants, catalog, segments, segment_count, bodies, origin):
    asteroid_keys, kbo_keys, ring_keys = validate_catalog(constants, catalog, segments)
    unit = (constants['AU']*1000)**3 / 86400**2
    by_id = {r['id']: r for r in catalog['bodies']}
    included_keys = set()
    if len(bodies) != 27 or len(ALL_IDENTITIES) != 16:
        raise ValueError('Unexpected current model')
    for body, (identity, name, key) in zip(bodies[11:], ALL_IDENTITIES):
        row = by_id[identity]
        if (body.name != name or (row['name'], row['constant']) != (name, key)
                or not isclose(body.mass*G, constants[key]*unit, rel_tol=3e-15, abs_tol=0.)):
            raise ValueError('Runtime/catalog mass mismatch')
        included_keys.add(key)
    def group(keys):
        return dict(count=len(keys), gm_m3_s2=fsum(constants[k] for k in sorted(keys))*unit)
    groups = dict(asteroids_all=group(asteroid_keys), asteroids_included=group(included_keys),
        asteroids_missing=group(asteroid_keys-included_keys), kuiper_belt_objects=group(kbo_keys),
        kuiper_ring=group(ring_keys))
    missing = sorted((r for r in catalog['bodies'] if r['constant'] in asteroid_keys-included_keys),
        key=lambda r: (-constants[r['constant']], r['id']))
    by_name = {b.name: b for b in bodies}
    def vector(body):
        p = body.position
        return np.array([p.x, p.y, p.z])
    sun = vector(by_name['Sun'])
    radius = 44*constants['AU']*1000
    ring_gm = groups['kuiper_ring']['gm_m3_s2']
    forces = {}
    for name in ('Earth', 'Moon', 'Mars'):
        p = vector(by_name[name])-sun
        variants = [inner_ring_acceleration(p, radius, ring_gm, n, phase)
            for n, phase in ((36, 0.), (36, np.pi/36), (72, 0.), (144, 0.))]
        error = max(float(np.linalg.norm(v-variants[-1])) for v in variants[:-1])
        if error > 1e-27:
            raise RuntimeError('Inner ring quadrature convergence failed')
        forces[name] = dict(position_over_ring_radius=float(np.linalg.norm(p)/radius),
            acceleration_m_per_s2=variants[-1].tolist(), magnitude_m_per_s2=float(np.linalg.norm(variants[-1])),
            quadrature_phase_spread_m_per_s2=error)
    relative = np.array(forces['Moon']['acceleration_m_per_s2'])-forces['Earth']['acceleration_m_per_s2']
    return dict(schema=1, epoch_jd_tdb=origin.epoch_jd_tdb, duration_seconds=31557600,
        runtime_dataset_sha256=origin.dataset_sha256, runtime_bodies=len(bodies),
        sources=dict(header=dict(url=HEADER_URL, sha256=HEADER_SHA), memorandum=catalog['source'],
            catalog_sha256=CATALOG_SHA, spk_metadata_sha256=MANIFEST_SHA,
            ring_geometry=dict(url=PAPER_URL, section='2.2', radius_au=44, equal_masses=36)),
        spk=dict(url='https://ssd.jpl.nasa.gov/ftp/eph/small_bodies/asteroids_de441/sb441-n373s.bsp',
            full_bytes=982106112, downloaded_metadata_bytes=16384, segments=segment_count,
            covered_bodies=len(segments), center=10, frame=1, type=2,
            note='374 segments, 373 identities: Ganymed has two successive time intervals; one covers the selected year.'),
        mass_groups=groups, included_asteroid_mass_fraction=groups['asteroids_included']['gm_m3_s2']/groups['asteroids_all']['gm_m3_s2'],
        next_by_mass=[dict(**r, gm_m3_s2=constants[r['constant']]*unit) for r in missing[:16]],
        inner_kuiper_ring_diagnostic=dict(radius_metres=radius, gm_m3_s2=ring_gm,
            forces=forces, moon_minus_earth_magnitude_m_per_s2=float(np.linalg.norm(relative)),
            note='Instantaneous uniform ring quadrature in a heliocentric frame. No propagated orbit, error bound, moving ring initial states or ring-only annual forecast.'),
        checks_passed=True,
        conclusion='Obtain and validate the missing 327 individual asteroid initial states before replacing them by a circular main-belt ring. KBOs and the 44-au ring are a separate source group.',
        limitation='Mass fraction is not acceleration or orbit error fraction. Ranking is by GM, not actual dynamical influence. SB441 extraction and mass consistency do not independently validate JPL ephemeris accuracy. No runtime physics change.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    args = parser.parse_args()
    catalog = pinned_json('de441-perturber-catalog.json', CATALOG_SHA)
    manifest = pinned_json('sb441-catalog-ranges.json', MANIFEST_SHA)
    header_path = SOURCE_DIR / 'validation/de441-header.441'
    memo_path = Path('.tools/sb441-perturbers.pdf')
    header = header_path.read_bytes()
    if args.download:
        memo_path.parent.mkdir(exist_ok=True)
        header = fetch(HEADER_URL)
        memo_path.write_bytes(fetch(catalog['source']['url']))
    if hashlib.sha256(header).hexdigest() != HEADER_SHA:
        raise ValueError('Pinned DE441 header changed')
    if args.download and hashlib.sha256(memo_path.read_bytes()).hexdigest() != catalog['source']['sha256']:
        raise ValueError('Pinned memorandum changed')
    blocks = source_blocks(manifest, args.download)
    bodies, origin = solar_system_asteroids_full()
    segments, count = decode_inventory(manifest, blocks, origin.epoch_jd_tdb, 31557600)
    report = audit(decode_header(header), catalog, segments, count, bodies, origin)
    Path('docs/perturber-audit.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print('mass_groups', report['mass_groups'])
    print('included_fraction', report['included_asteroid_mass_fraction'], 'checks_passed', report['checks_passed'])


if __name__ == '__main__':
    main()
