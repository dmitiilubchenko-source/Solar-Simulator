"""343-body source grid, preserved parents and cancellation-safe force screen."""
from copy import deepcopy
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import struct
import subprocess

import numpy as np
import pytest

from scripts.fetch_asteroid_catalog import (inputs, year_blocks, decode_year,
    initial_document, trial_system, INITIAL_SHA)
from scripts.assess_asteroid_catalog import individual_acceleration, differential_acceleration, screen
from scripts.assess_resolved_moon import states
from solar_simulator.perturbers import solar_system_asteroids_full


def data():
    catalog, manifest, descriptors, constants = inputs()
    blocks = year_blocks(manifest)
    ids = {r['id'] for r in catalog['bodies'] if r['group'] == 'asteroid'}
    records = decode_year(manifest, blocks, descriptors, ids)
    return catalog, manifest, descriptors, constants, blocks, records


def test_entire_source_reproduces_initial_states_and_preserves_all_parent_values():
    catalog, manifest, _, constants, _, records = data()
    assert len(records) == 343
    assert records[2001036][0, 1]*2 == 8*86400
    assert records[2000001][0, 1]*2 == 32*86400
    document = initial_document(catalog, manifest, constants, records)
    raw = (json.dumps(document, indent=2)+'\n').encode()
    assert hashlib.sha256(raw).hexdigest() == INITIAL_SHA
    assert Path('docs/asteroids-343-initial.json').read_bytes() == raw
    assert all(v == {'position_metres': 0., 'velocity_m_per_s': 0.} for v in document['existing_sixteen_crosscheck'].values())
    parent, _ = solar_system_asteroids_full()
    full = trial_system(document)
    assert len(full) == 354 and np.array_equal(states(full[:27]), states(parent))
    assert [(b.name, b.mass) for b in full[:27]] == [(b.name, b.mass) for b in parent]
    selected = trial_system(document, [2000209, 2000094])
    assert len(selected) == 29 and {b.name for b in selected[27:]} == {'Dido', 'Aurora'}


@pytest.mark.parametrize('change', ['directory', 'pointer', 'grid', 'nan', 'missing'])
def test_invalid_source_grids_and_addresses_are_rejected(change):
    catalog, manifest, descriptors, _, blocks, _ = data()
    manifest = deepcopy(manifest)
    blocks = dict(blocks)
    identity = 2000001
    key = f'records-{identity}'
    if change == 'directory':
        raw = bytearray(blocks[f'tail-{identity}']);struct.pack_into('<d', raw, 8, 0.)
        blocks[f'tail-{identity}'] = bytes(raw)
    if change == 'pointer':
        next(e for e in manifest['entries'] if e['role'] == key)['byte_range'][0] += 8
    if change in ('grid', 'nan'):
        raw = bytearray(blocks[key]);struct.pack_into('<d', raw, 0 if change == 'grid' else 16, 0. if change == 'grid' else float('nan'))
        blocks[key] = bytes(raw)
    if change == 'missing': blocks.pop(key)
    ids = {r['id'] for r in catalog['bodies'] if r['group'] == 'asteroid'}
    with pytest.raises(ValueError): decode_year(manifest, blocks, descriptors, ids)


@pytest.mark.parametrize('change', ['mass', 'position', 'future', 'parent', 'duplicate'])
def test_trial_catalogue_cannot_silently_change_pinned_states(change):
    doc = json.loads(Path('docs/asteroids-343-initial.json').read_text())
    if change == 'mass': doc['bodies'][20]['gm_m3_s2'] *= 1.001
    if change == 'position': doc['bodies'][20]['position'][0] += 1.
    if change == 'future': doc['bodies'][20]['states'] = []
    if change == 'parent': doc['base_origin']['dataset_sha256'] = '0'*64
    if change == 'duplicate': doc['bodies'][20] = doc['bodies'][21]
    with pytest.raises(ValueError): trial_system(doc)


def test_trial_selection_rejects_existing_unknown_and_duplicate_ids():
    doc = json.loads(Path('docs/asteroids-343-initial.json').read_text())
    for selected in ([2000001], [9876543], [2000209, 2000209]):
        with pytest.raises(ValueError): trial_system(doc, selected)


def test_differential_force_agrees_with_direct_force_in_resolved_geometry():
    sources = np.array([[10., 3., -7.], [-5., 2., 11.]])
    mu, first, rho = np.array([2., 9.]), np.array([.2, -.3, .7]), np.array([.01, .03, -.02])
    expected = individual_acceleration(sources, mu, first+rho)-individual_acceleration(sources, mu, first)
    assert np.allclose(differential_acceleration(sources, mu, first, rho), expected, rtol=2e-12, atol=1e-17)


def test_differential_force_resolves_a_pair_too_small_for_direct_subtraction():
    # 80-digit scalar reference; neither reference target is rounded in float64.
    with localcontext() as context:
        context.prec = 80
        d, rho, mu = Decimal('1e16'), Decimal('1e-5'), Decimal('1e10')
        expected = float(mu/(d-rho)**2-mu/d**2)
    direct = individual_acceleration([[1e16, 0., 0.]], [1e10], [1e-5, 0., 0.])
    direct -= individual_acceleration([[1e16, 0., 0.]], [1e10], [0., 0., 0.])
    assert direct[0, 0] == 0.
    stable = differential_acceleration([[1e16, 0., 0.]], [1e10], [0., 0., 0.], [1e-5, 0., 0.])
    assert stable[0, 0] == pytest.approx(expected, rel=5e-16, abs=0.)
    assert np.all(stable[0, 1:] == 0.)


@pytest.mark.parametrize('source,mu,target', [([[0., 0., 0.]], [1.], [0., 0., 0.]),
    ([[1., 0., 0.]], [0.], [0., 0., 0.]), ([[1., 0., float('nan')]], [1.], [0., 0., 0.]),
    ([[1., 0., 0.]], [1., 2.], [0., 0., 0.])])
def test_force_screen_rejects_singular_or_invalid_data(source, mu, target):
    with pytest.raises(ValueError): individual_acceleration(source, mu, target)
    with pytest.raises(ValueError): differential_acceleration(source, mu, target, [0., 0., 0.])


def test_force_screen_has_complete_missing_group_and_reproducible_selection():
    catalog, _, _, constants, _, records = data()
    result = screen(catalog, records, constants)
    assert result['missing_count'] == 327 and result['samples'] == 13
    assert len(result['selected_candidates']) == 15
    for target in result['targets'].values():
        assert 0 < target['maximum_net_acceleration_m_per_s2'] <= target['maximum_sum_of_individual_magnitudes_m_per_s2']
        values = [r['maximum_acceleration_m_per_s2'] for r in target['top_sixteen']]
        assert values == sorted(values, reverse=True)
    saved = json.loads(Path('docs/asteroids-343-assessment.json').read_text())
    assert saved['force_screen'] == result


def test_git_line_ending_filters_preserve_pinned_scientific_source_bytes():
    # Read-only clean-filter probe; no index or global Git settings are changed.
    for path in ('docs/asteroids-343-initial.json', 'src/solar_simulator/data/earth-j2-20261008.json',
            'scripts/sb441-343-ranges.json', 'scripts/validation/de441-header.441'):
        expected = subprocess.run(['git', 'hash-object', '--no-filters', path], check=True,
            capture_output=True, text=True).stdout.strip()
        filtered = subprocess.run(['git', '-c', 'core.autocrlf=true', 'hash-object', '--path', path, path],
            check=True, capture_output=True, text=True).stdout.strip()
        assert filtered == expected
