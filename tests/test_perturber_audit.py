"""Independent source inventory and analytic checks of the ring diagnostic."""
from copy import deepcopy
import hashlib
import json
from math import sqrt
from pathlib import Path
import struct

import numpy as np
import pytest
from scipy.special import ellipk

from scripts.audit_perturbers import (CATALOG_SHA, MANIFEST_SHA, SOURCE_DIR,
    pinned_json, source_blocks, decode_inventory, validate_catalog,
    inner_ring_acceleration, audit)
from scripts.fetch_figure_profile import HEADER_SHA, decode_header
from solar_simulator.perturbers import solar_system_asteroids_full


def inventory():
    catalog = pinned_json('de441-perturber-catalog.json', CATALOG_SHA)
    manifest = pinned_json('sb441-catalog-ranges.json', MANIFEST_SHA)
    blocks = source_blocks(manifest)
    raw = (SOURCE_DIR / 'validation/de441-header.441').read_bytes()
    assert hashlib.sha256(raw).hexdigest() == HEADER_SHA
    return catalog, manifest, blocks, decode_header(raw)


def test_offline_catalog_covers_the_actual_spk_and_all_header_masses():
    catalog, manifest, blocks, constants = inventory()
    segments, count = decode_inventory(manifest, blocks, 2461321.5, 31557600)
    asteroid_keys, kbo_keys, ring_keys = validate_catalog(constants, catalog, segments)
    assert (len(asteroid_keys), len(kbo_keys), len(ring_keys)) == (343, 30, 36)
    assert count == 374 and len(segments) == 373
    assert 2001036 in segments  # Ganymed's two disjoint intervals are valid.
    assert sum(map(len, blocks.values())) == 16384
    bodies, origin = solar_system_asteroids_full()
    before = [(b.name, b.mass, b.position.x, b.position.y, b.position.z) for b in bodies]
    report = audit(constants, catalog, segments, count, bodies, origin)
    assert report['checks_passed'] and report['runtime_dataset_sha256'] == origin.dataset_sha256
    groups = report['mass_groups']
    assert groups['asteroids_missing']['count'] == 327
    assert groups['asteroids_included']['count'] == 16
    assert .71604 < report['included_asteroid_mass_fraction'] < .71605
    assert groups['asteroids_all']['gm_m3_s2'] == pytest.approx(
        groups['asteroids_missing']['gm_m3_s2'] + groups['asteroids_included']['gm_m3_s2'], rel=3e-16)
    assert [r['name'] for r in report['next_by_mass'][:4]] == ['Dido', 'Aurora', 'Doris', 'Bertha']
    assert before == [(b.name, b.mass, b.position.x, b.position.y, b.position.z) for b in bodies]
    saved = json.loads(Path('docs/perturber-audit.json').read_text(encoding='utf-8'))
    assert saved == report


@pytest.mark.parametrize('change', ['cycle', 'count', 'previous', 'frame', 'address', 'coverage', 'missing'])
def test_daf_corruption_and_missing_year_are_rejected(change):
    _, manifest, blocks, _ = inventory()
    blocks = dict(blocks)
    mutable = bytearray(blocks['summary-3'])
    if change == 'cycle':
        struct.pack_into('<d', mutable, 0, 3.)
    elif change == 'count':
        struct.pack_into('<d', mutable, 16, 25.5)
    elif change == 'previous':
        struct.pack_into('<d', mutable, 8, 7.)
    elif change == 'frame':
        struct.pack_into('<i', mutable, 48, 2)
    elif change == 'address':
        struct.pack_into('<i', mutable, 56, -1)
    elif change == 'coverage':
        with pytest.raises(ValueError):
            segments, _ = decode_inventory(manifest, blocks, 3000000., 31557600)
            catalog, _, _, constants = inventory()
            validate_catalog(constants, catalog, segments)
        return
    elif change == 'missing':
        blocks.pop('summary-3')
        with pytest.raises(ValueError):
            decode_inventory(manifest, blocks, 2461321.5, 31557600)
        return
    blocks['summary-3'] = bytes(mutable)
    with pytest.raises(ValueError):
        decode_inventory(manifest, blocks, 2461321.5, 31557600)


@pytest.mark.parametrize('change', ['duplicate', 'mass', 'group', 'number', 'ring', 'missing_kbo'])
def test_mass_inventory_conflicts_are_rejected(change):
    catalog, manifest, blocks, constants = inventory()
    catalog = deepcopy(catalog)
    segments, _ = decode_inventory(manifest, blocks, 2461321.5, 31557600)
    if change == 'duplicate': catalog['bodies'][1]['id'] = catalog['bodies'][0]['id']
    if change == 'mass': catalog['bodies'][1]['gm_au3_per_day2'] *= 1.001
    if change == 'group': catalog['bodies'][1]['group'] = 'unknown'
    if change == 'number': catalog['bodies'][1]['number'] += 1
    if change == 'ring': constants['MA8201'] *= 1.001
    if change == 'missing_kbo': catalog['bodies'].pop()
    with pytest.raises(ValueError): validate_catalog(constants, catalog, segments)


def test_ring_axial_force_and_interior_tidal_gradient_have_correct_sign_and_scale():
    radius, mu, z = 10., 23., .3
    actual = inner_ring_acceleration([0., 0., z], radius, mu)
    assert actual[2] == pytest.approx(-mu*z/(radius*radius+z*z)**1.5, rel=5e-16)
    assert np.linalg.norm(actual[:2]) < 1e-17
    # Near the centre: outward in the plane, restoring along the pole.
    step = 1e-4*radius
    columns = [(inner_ring_acceleration(np.eye(3)[i]*step, radius, mu)
        -inner_ring_acceleration(-np.eye(3)[i]*step, radius, mu))/(2*step) for i in range(3)]
    jacobian = np.column_stack(columns)
    expected = mu/(2*radius**3)*np.diag([1., 1., -2.])
    assert np.allclose(jacobian, expected, rtol=2e-8, atol=1e-13)
    assert abs(np.trace(jacobian)) < 1e-9  # Laplace equation away from the ring.


def test_ring_force_matches_gradient_of_independent_elliptic_potential():
    radius, mu = 10., 23.
    p = np.array([.4, .2, .1])
    def potential(x):
        rho = np.linalg.norm(x[:2])
        d = sqrt((radius+rho)**2+x[2]**2)
        return -2*mu/np.pi*ellipk(4*radius*rho/d**2)/d
    step = .001*radius
    force = []
    for axis in np.eye(3):
        derivative = (potential(p-2*step*axis)-8*potential(p-step*axis)
            +8*potential(p+step*axis)-potential(p+2*step*axis))/(12*step)
        force.append(-derivative)
    assert np.allclose(inner_ring_acceleration(p, radius, mu), force, rtol=2e-8, atol=1e-13)


@pytest.mark.parametrize('position,radius,gm,points', [([1, 0, 0], 10., 1., 72),
    ([0, 0, float('nan')], 10., 1., 72), ([0, 0], 10., 1., 72),
    ([0, 0, 0], -1., 1., 72), ([0, 0, 0], 10., 0., 72), ([0, 0, 0], 10., 1., 2)])
def test_ring_diagnostic_rejects_outer_or_invalid_geometry(position, radius, gm, points):
    with pytest.raises(ValueError): inner_ring_acceleration(position, radius, gm, points)
