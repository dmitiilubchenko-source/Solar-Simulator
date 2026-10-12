"""Independent CSPICE interpolation/frame/velocity check of all 343 asteroids."""
import hashlib
import json
from pathlib import Path
import sys
import uuid

import numpy as np
sys.path.insert(0, str(Path('.tools/orientation-libs').resolve()))
import spiceypy as spice

if __package__:
    from .fetch_asteroid_catalog import (inputs, year_blocks, decode_year,
        heliocentric_state, rotation, YEAR_MANIFEST_SHA)
    from .fetch_resolved_moon import MOON_EPOCHS
else:
    from fetch_asteroid_catalog import (inputs, year_blocks, decode_year,
        heliocentric_state, rotation, YEAR_MANIFEST_SHA)
    from fetch_resolved_moon import MOON_EPOCHS


def main():
    catalog, manifest, descriptors, _ = inputs()
    rows = [r for r in catalog['bodies'] if r['group'] == 'asteroid']
    records = decode_year(manifest, year_blocks(manifest), descriptors, {r['id'] for r in rows})
    folder = Path('.tools/sb441-343')
    folder.mkdir(exist_ok=True)
    path = folder / ('cspice-subset-'+uuid.uuid4().hex+'.bsp')
    handle = spice.spkopn(str(path.resolve()), 'Pinned SB441 343 asteroid year subset', 0)
    try:
        for row in rows:
            values = records[row['id']]
            start, end = values[0, 0]-values[0, 1], values[-1, 0]+values[-1, 1]
            spice.spkw02(handle, row['id'], 10, 'J2000', start, end, 'SB441 original coefficients',
                2*values[0, 1], len(values), 7, values[:, 2:].ravel(), start)
    finally:
        spice.spkcls(handle)
    transform = rotation()
    reference_transform = spice.pxform('J2000', 'ECLIPJ2000', 0.)
    if not np.allclose(transform, reference_transform, rtol=0., atol=2e-16):
        raise RuntimeError('CSPICE ecliptic frame mismatch')
    results = {}
    spice.furnsh(str(path.resolve()))
    try:
        for row in rows:
            values = records[row['id']]
            boundaries = (values[:, 0]-values[:, 1])/86400+2451545
            epochs = sorted(set(MOON_EPOCHS + [float(jd) for jd in boundaries
                if MOON_EPOCHS[0] <= jd <= MOON_EPOCHS[-1]]))
            maximum = np.zeros(2)
            for jd in epochs:
                oracle, _ = spice.spkgeo(row['id'], (jd-2451545)*86400, 'ECLIPJ2000', 10)
                actual = (heliocentric_state(values, jd).reshape(2, 3)@transform.T).ravel()
                delta = actual-oracle*1000
                maximum = np.maximum(maximum, [np.linalg.norm(delta[:3]), np.linalg.norm(delta[3:])])
            if maximum[0] > .01 or maximum[1] > 1e-8:
                raise RuntimeError(f'SB441/CSPICE mismatch: {row["name"]} {maximum}')
            results[row['name']] = dict(id=row['id'], samples=len(epochs),
                maximum_position_metres=float(maximum[0]), maximum_velocity_m_per_s=float(maximum[1]))
    finally:
        spice.unload(str(path.resolve()))
        path.unlink()
    report = dict(oracle='CSPICE spkgeo on a subset built from original SB441-N373s coefficients',
        spiceypy=spice.__version__, manifest_sha256=YEAR_MANIFEST_SHA,
        packed_source_sha256=hashlib.sha256(Path('scripts/validation/sb441-343-year.bin').read_bytes()).hexdigest(),
        bodies=results, body_count=len(results), samples=sum(r['samples'] for r in results.values()),
        maximum_position_metres=max(r['maximum_position_metres'] for r in results.values()),
        maximum_velocity_m_per_s=max(r['maximum_velocity_m_per_s'] for r in results.values()),
        record_boundaries_included=True, checks_passed=True,
        limitation='Checks source reading, interpolation, analytic derivative and frame. Does not independently establish the physical accuracy of SB441 or match the internal fitted asteroid trajectories of DE441.')
    Path('docs/asteroids-343-source-validation.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print('343 asteroid source checks:', {k: v for k, v in report.items() if k != 'bodies'}, flush=True)


if __name__ == '__main__':
    main()
