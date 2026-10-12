"""Screen missing asteroid forces on JPL snapshots and profile trial EIH.

Future source vectors are used solely to assess forces, never as solver input
after initialization. Instantaneous force screening is not an orbit forecast.
"""
import argparse
import hashlib
import json
from math import fsum
from pathlib import Path
import platform
import statistics
import time

import numpy as np
from solar_simulator.accuracy import evolve_accurate
from solar_simulator.oblateness import sun_earth_moon_quadrupoles
from solar_simulator.perturbers import solar_system_asteroids_full
from solar_simulator.relativity import C, _eih_acceleration
from solar_simulator.simulation import G

if __package__:
    from .fetch_asteroid_catalog import (inputs, year_blocks, decode_year,
        trial_system, INITIAL_SHA, YEAR_MANIFEST_SHA, heliocentric_state, rotation)
    from .fetch_asteroid_data import ALL_IDENTITIES
    from .assess_resolved_moon import states
    from .assess_relative_coordinates import REFERENCE_SHA256
    from .assess_solar_j2 import PLANET_REFERENCE_SHA256
    from .independent_eih_rust import load_oracle
else:
    from fetch_asteroid_catalog import (inputs, year_blocks, decode_year,
        trial_system, INITIAL_SHA, YEAR_MANIFEST_SHA, heliocentric_state, rotation)
    from fetch_asteroid_data import ALL_IDENTITIES
    from assess_resolved_moon import states
    from assess_relative_coordinates import REFERENCE_SHA256
    from assess_solar_j2 import PLANET_REFERENCE_SHA256
    from independent_eih_rust import load_oracle


def individual_acceleration(sources, mu, target):
    p, m, q = np.asarray(sources, dtype=float), np.asarray(mu, dtype=float), np.asarray(target, dtype=float)
    if (m.ndim != 1 or p.shape != (len(m), 3) or q.shape != (3,)
            or not all(np.all(np.isfinite(a)) for a in (p, m, q)) or np.any(m <= 0)):
        raise ValueError('Finite source positions, target and positive GM required')
    with np.errstate(over='raise', divide='raise', invalid='raise'):
        delta = p-q
        distance = np.linalg.norm(delta, axis=1)
        if np.any(distance == 0):
            raise ValueError('Source/target collision')
        return delta*(m/distance**3)[:, None]


def differential_acceleration(sources, mu, first, relative):
    """Stable a(second)-a(first), without subtracting nearly equal forces.

    d points from first target to source, h=(rho²-2*d.rho)/d².
    expm1(-3/2*log1p(h)) computes |d-rho|^-3/|d|^-3 minus 1.
    """
    p, m, q, rho = (np.asarray(v, dtype=float) for v in (sources, mu, first, relative))
    if (m.ndim != 1 or p.shape != (len(m), 3) or q.shape != (3,) or rho.shape != (3,)
            or not all(np.all(np.isfinite(a)) for a in (p, m, q, rho)) or np.any(m <= 0)):
        raise ValueError('Invalid differential source geometry')
    with np.errstate(over='raise', divide='raise', invalid='raise'):
        d = p-q
        r2 = np.sum(d*d, axis=1)
        if np.any(r2 == 0) or np.any(np.linalg.norm(d-rho, axis=1) == 0):
            raise ValueError('Source/target collision')
        h = (rho@rho-2*(d@rho))/r2
        if np.any(h <= -1):
            raise ValueError('Unresolved differential source geometry')
        correction = np.expm1(-1.5*np.log1p(h))
        return (d*correction[:, None]-rho*(1+correction[:, None]))*(m/r2**1.5)[:, None]


def summed(values):
    return np.array([fsum(values[:, i]) for i in range(3)])


def pinned_document(path, digest):
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Pinned force-screen input changed')
    return json.loads(raw)


def screen(catalog, records, constants):
    planets = pinned_document('docs/solar-system-reference.json', PLANET_REFERENCE_SHA256)
    pair = pinned_document('docs/solar-system-moon-reference.json', REFERENCE_SHA256)
    included = {identity for identity, _, _ in ALL_IDENTITIES}
    missing = [r for r in catalog['bodies'] if r['group'] == 'asteroid' and r['id'] not in included]
    scale = (constants['AU']*1000)**3/86400**2
    mu = np.array([constants[r['constant']]*scale for r in missing])
    body_p = {b['name']: b for b in planets['bodies']}
    body_q = {b['name']: b for b in pair['bodies']}
    transform = rotation()
    contributions = {name: [] for name in ('Sun', 'Earth', 'Moon', 'Mars', 'Moon-minus-Earth')}
    for index, jd in enumerate(planets['epochs_jd_tdb']):
        q_index = pair['epochs_jd_tdb'].index(jd)
        sun = np.array(body_p['Sun']['states'][index]['position'])
        targets = dict(Sun=np.zeros(3),
            Earth=np.array(body_q['Earth']['states'][q_index]['position'])-sun,
            Moon=np.array(body_q['Moon']['states'][q_index]['position'])-sun,
            Mars=np.array(body_p['Mars']['states'][index]['position'])-sun)
        sources = np.array([heliocentric_state(records[r['id']], jd)[:3]@transform.T for r in missing])
        for name, target in targets.items():
            contributions[name].append(individual_acceleration(sources, mu, target))
        contributions['Moon-minus-Earth'].append(differential_acceleration(sources, mu,
            targets['Earth'], targets['Moon']-targets['Earth']))
    report = {}
    for name, samples in contributions.items():
        values = np.array(samples)
        magnitudes = np.linalg.norm(values, axis=2)
        maxima = magnitudes.max(axis=0)
        ranking = np.argsort(-maxima, kind='stable')
        total = np.array([summed(v) for v in values])
        report[name] = dict(maximum_net_acceleration_m_per_s2=float(np.linalg.norm(total, axis=1).max()),
            maximum_sum_of_individual_magnitudes_m_per_s2=float(np.max(np.sum(magnitudes, axis=1))),
            initial_net_vector_m_per_s2=total[0].tolist(),
            top_sixteen=[dict(id=missing[i]['id'], name=missing[i]['name'],
                maximum_acceleration_m_per_s2=float(maxima[i])) for i in ranking[:16]])
    selection = sorted({r['id'] for name in ('Earth', 'Mars', 'Moon-minus-Earth')
        for r in report[name]['top_sixteen'][:8]})
    indices = [i for i, row in enumerate(missing) if row['id'] in selection]
    for name, samples in contributions.items():
        omitted = [summed(v)-summed(v[indices]) for v in samples]
        report[name]['screen_selection_remaining_net_acceleration_m_per_s2'] = float(np.linalg.norm(omitted, axis=1).max())
    rows = {row['id']: row for row in missing}
    return dict(samples=len(planets['epochs_jd_tdb']), epochs_jd_tdb=planets['epochs_jd_tdb'],
        missing_count=len(missing), targets=report,
        selection_rule='Union of top 8 missing bodies by maximum individual acceleration at Earth, Mars and by Moon-Earth differential acceleration on 13 JPL epochs; exploratory, not an optimal dynamical truncation.',
        selected_candidates=[dict(id=identity, name=rows[identity]['name']) for identity in selection],
        limitation='Forces evaluated along source/JPL snapshots. Maxima apply only to the 13 sampled epochs, not the entire interval. No annual orbit error estimate or prescribed trajectories in a simulation.')


def measured_call(function, repetitions=12):
    function()
    batches = []
    for _ in range(5):
        start = time.perf_counter()
        for _ in range(repetitions):
            function()
        batches.append((time.perf_counter()-start)/repetitions)
    return dict(median_seconds=statistics.median(batches), min_seconds=min(batches), max_seconds=max(batches),
        batches=len(batches), calls_per_batch=repetitions)


def profile(document, selection, *, integrate_day=False):
    base, origin = solar_system_asteroids_full()
    full = trial_system(document)
    candidates = trial_system(document, selection)
    oracle = load_oracle()
    report = {}
    for name, bodies in (('current_27', base), ('screen_candidates', candidates), ('all_354', full)):
        values = states(bodies)
        p, v, m = values[:, :3], values[:, 3:], np.array([b.mass for b in bodies])
        mu = m*G
        names = [b.name for b in bodies]
        e, moon = names.index('Earth'), names.index('Moon')
        relative = (e, moon, p[moon]-p[e])
        actual = _eih_acceleration(p, v, m, C, relative)
        independent = oracle(p, v, mu, C, relative)
        difference = float(np.max(np.linalg.norm(actual-independent, axis=1)))
        if difference > 3e-16:
            raise RuntimeError('Trial EIH force/oracle disagreement')
        report[name] = dict(bodies=len(bodies),
            python_eih=measured_call(lambda: _eih_acceleration(p, v, m, C, relative)),
            developer_rust_scalar_eih=measured_call(lambda: oracle(p, v, mu, C, relative)),
            maximum_force_oracle_difference_m_per_s2=difference)
        if integrate_day:
            figures = sun_earth_moon_quadrupoles(base, origin)
            start = time.perf_counter()
            final = evolve_accurate(bodies, 86400., physics='eih-1pn', figures=figures,
                relative_pair=('Earth', 'Moon'), rtol=3e-14, position_atol=1e-5, velocity_atol=1e-11)
            report[name]['day_integration_seconds'] = time.perf_counter()-start
            report[name]['day_bodies'] = len(final)
        print('profile', name, report[name], flush=True)
    return dict(machine=platform.platform(), python=platform.python_version(), numpy=np.__version__,
        models=report, independent_force_source_sha256=oracle.source_sha256,
        limitation='Measured wall times on this machine. Rust is the independent developer oracle, not the production EIH backend. A one-day timing is not a measured yearly runtime; trial systems are not registered runtime presets.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--integrate-day', action='store_true')
    args = parser.parse_args()
    catalog, manifest, descriptors, constants = inputs()
    identities = {r['id'] for r in catalog['bodies'] if r['group'] == 'asteroid'}
    records = decode_year(manifest, year_blocks(manifest), descriptors, identities)
    initial = pinned_document('docs/asteroids-343-initial.json', INITIAL_SHA)
    force_screen = screen(catalog, records, constants)
    timings = profile(initial, [r['id'] for r in force_screen['selected_candidates']], integrate_day=args.integrate_day)
    result = dict(schema=1, source_manifest_sha256=YEAR_MANIFEST_SHA, initial_catalogue_sha256=INITIAL_SHA,
        force_screen=force_screen, profiling=timings, checks_passed=True,
        next_step='Use the measured scaling to port production EIH to Rust with a separate oracle before a full 354-body annual benchmark. Screen selection is a diagnostic candidate set, not yet validated as a runtime model.')
    Path('docs/asteroids-343-assessment.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print('screen candidates', force_screen['selected_candidates'], 'checks_passed', True, flush=True)


if __name__ == '__main__':
    main()
