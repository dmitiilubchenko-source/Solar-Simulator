"""Canonical state identity, incompatible-schema rejection and actual restart."""
from dataclasses import replace
import hashlib
import json

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from scripts.canonical_checkpoint import (CanonicalCheckpoint, CanonicalDOP853,
    canonical_text, from_document, to_document, save, load, velocity_export, parse_json,
    verify_sources, evolve, CORE_SOURCES, RUNNING_ROOT)
from scripts.canonical_initial import SIUnits
from scripts.rigid_pn_model import Parameters, rhs
from scripts.nbody_pn_spin import Parameters as PointParameters
from solar_simulator.rotation import RigidFigure


P = Parameters(PointParameters((.3, .7, .05), float(np.sqrt(1e5))),
               RigidFigure(.3, (.002, .0025, .003), .15), 0)
Y = np.r_[np.array([[[.56, 0., 0.], [-.24, 0., 0.], [3.5, .4, .6]],
                   [[0., .257, 0.], [0., -.257, 0.], [-.003, .025, .004]],
                   [[.003, -.004, .002], [-.002, .001, .003], [.0002, .0003, -.0001]]]).ravel(),
          [1., 0., 0., 0.]]


def fixture_checkpoint():
    meta = dict(frame=dict(name='synthetic fixed frame', centre='canonical-ADM-centres',
        spin_basis='finite-H-spatial-Euclidean', time_coordinate='model-coordinate-time',
        epoch_jd=None, evolution='fixed-no-reboost'), units=dict(kind='synthetic-G1'),
        integration=dict(method='canonical-per-block-DOP853', rtol=1e-11,
                         atol=[1e-13]*len(Y), max_step=.02),
        provenance=dict(interpretation='synthetic initial state', physical_mapping_certified=False,
                        sources=[dict(path='synthetic-policy', sha256='a'*64)]))
    return CanonicalCheckpoint(P, tuple(Y), tuple(Y), 0., canonical_text(meta))


def rehash(document):
    d = dict(document); d.pop('payload_sha256')
    document['payload_sha256'] = hashlib.sha256(canonical_text(d).encode('utf-8')).hexdigest()
    return document


def test_bitwise_roundtrip_preserves_raw_q_negative_zero_and_detached_metadata(tmp_path):
    cp = fixture_checkpoint(); current = np.array(cp.state)
    current[1] = -0.; current[-4:] *= 1+2e-10
    cp = replace(cp, state=tuple(current), time=.1)
    path = tmp_path/'canonical state with spaces.json'; save(path, cp); loaded = load(path)
    assert np.array_equal(np.array(loaded.state).view(np.uint64), current.view(np.uint64))
    assert np.array_equal(np.array(loaded.initial).view(np.uint64), Y.view(np.uint64))
    assert loaded.parameters == cp.parameters and loaded.metadata_json == cp.metadata_json
    assert to_document(loaded) == to_document(cp)
    detached = loaded.metadata; detached['frame']['name'] = 'changed'
    assert loaded.metadata['frame']['name'] == 'synthetic fixed frame'
    with pytest.raises(FileExistsError):
        save(path, cp)


def test_legacy_velocity_and_export_documents_cannot_be_reimported():
    cp = fixture_checkpoint()
    for old in [dict(schema=9, bodies=[]), dict(schema=10, bodies=[], rotations=[]), velocity_export(cp)]:
        with pytest.raises(ValueError):
            from_document(old)
    document = to_document(cp); document['state']['velocities'] = document['state'].pop('momenta')
    with pytest.raises(ValueError, match='canonical state'):
        from_document(rehash(document))


def test_payload_damage_and_scientific_metadata_changes_are_detected():
    cp = fixture_checkpoint(); doc = to_document(cp); doc['state']['momenta'][0][0] += 1e-8
    with pytest.raises(ValueError, match='SHA256'):
        from_document(doc)
    mutations = [
        lambda d: d.update(schema=True), lambda d: d.update(model='eih-velocity'),
        lambda d: d['metadata']['frame'].update(centre='harmonic-centres'),
        lambda d: d['metadata']['frame'].update(evolution='instantaneous COM reboost'),
        lambda d: d['metadata']['frame'].update(spin_basis='legacy-Newton-spin'),
        lambda d: d['metadata']['frame'].update(time_coordinate='proper-time'),
        lambda d: d['metadata']['provenance'].update(physical_mapping_certified=True),
        lambda d: d['metadata']['provenance']['sources'][0].update(sha256='bad'),
        lambda d: d['metadata']['integration'].update(atol=[0.]*len(Y)),
        lambda d: d['metadata']['integration'].update(rtol=True),
        lambda d: d['parameters']['figure'].update(mass=True),
        lambda d: d['state']['quaternion'].__setitem__(0, True),
        lambda d: d['state']['positions'][0].__setitem__(0, '0.56'),
        lambda d: d['state']['quaternion'].__setitem__(0, 1.01),
        lambda d: d['parameters'].update(figure_index=True),
        lambda d: d.update(elapsed_model_time=-.1),
        lambda d: d['state']['positions'][0].__setitem__(0, .55)]
    for change in mutations:
        document = to_document(cp); change(document)
        with pytest.raises(ValueError):
            from_document(rehash(document))


def test_nonfinite_and_duplicate_JSON_keys_are_rejected():
    for text in ['{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}', 'bad json']:
        with pytest.raises(ValueError):
            parse_json(text)
    doc = to_document(fixture_checkpoint()); doc['state']['spins'][0][0] = float('nan')
    with pytest.raises(ValueError):
        from_document(doc)


def test_SI_velocity_export_is_canonical_and_uses_saved_scales():
    cp = fixture_checkpoint(); meta = cp.metadata
    units = SIUnits(1.988e30, 1.495978707e11, 6.6743e-11)
    meta['units'] = dict(kind='SI-similarity', **vars(units))
    meta['frame']['time_coordinate'] = 'TDB-as-input-coordinate-time'; meta['frame']['epoch_jd'] = 2461321.5
    cp = replace(cp, metadata_json=canonical_text(meta))
    exported = velocity_export(loads_document(cp))
    model_v = rhs(0., np.array(cp.state), cp.parameters)[:9].reshape(3, 3)
    assert np.array_equal(np.array(exported['velocity_m_s']), model_v*units.velocity_m_s)
    assert not np.array_equal(model_v, Y[9:18].reshape(3, 3)/np.array(P.orbital.masses)[:, None])
    assert exported['metadata'] == meta


def loads_document(cp):
    return from_document(parse_json(json.dumps(to_document(cp))))


def test_file_restart_matches_full_path_without_frame_or_q_projection(tmp_path):
    cp = fixture_checkpoint(); controls = cp.metadata['integration']; times = np.linspace(0., .3, 17)
    def evolve(state, grid):
        return solve_ivp(lambda t, y: rhs(t, y, P), (float(grid[0]), float(grid[-1])), state,
            t_eval=grid, method=CanonicalDOP853, body_count=3, rtol=controls['rtol'],
            atol=controls['atol'], max_step=controls['max_step']).y.T
    full = evolve(cp.state, times); first = evolve(cp.state, times[:9])
    checkpoint = replace(cp, state=tuple(first[-1]), time=float(times[8]))
    path = tmp_path/'resume.json'; save(path, checkpoint); restored = load(path)
    last = evolve(restored.state, times[8:]); merged = np.vstack([first[:-1], last])
    scales = np.r_[np.repeat(np.linalg.norm(Y[:-4].reshape(3, 3, 3), axis=-1).ravel(), 3), np.ones(4)]
    assert np.max(abs(full-merged)/scales) < 1e-10
    assert restored.metadata_json == cp.metadata_json and restored.initial == cp.initial
    assert np.array_equal(np.array(restored.state).view(np.uint64), first[-1].view(np.uint64))


def test_worst_block_control_not_diluted_by_inactive_canonical_bodies():
    def system(count):
        y = np.zeros(9*count+4); y[0] = 1.; y[-4] = 1.
        def field(t, z):
            f = np.zeros_like(z); f[0] = z[3*count]; f[3*count] = -z[0]
            return f
        result = solve_ivp(field, (0., 6*np.pi), y, method=CanonicalDOP853,
            body_count=count, t_eval=np.linspace(0., 6*np.pi, 129), rtol=1e-9, atol=1e-12)
        return result
    small, large = system(2), system(20)
    for result in [small, large]:
        assert np.max(abs(result.y[0]-np.cos(result.t))) < 2e-8
    assert np.max(abs(small.y[0]-large.y[0])) < 1e-10
    with pytest.raises(ValueError):
        CanonicalDOP853(lambda t, y: y, 0., np.zeros(30), 1., body_count=3)


def test_source_verified_continuation_and_wrong_frame_grid_rejections(tmp_path):
    cp = fixture_checkpoint(); meta = cp.metadata
    meta['provenance']['sources'] = [dict(path=p, sha256=hashlib.sha256((RUNNING_ROOT/p).read_bytes()).hexdigest())
                                      for p in CORE_SOURCES]
    cp = replace(cp, metadata_json=canonical_text(meta))
    endpoint, states = evolve(cp, [0., .02, .04], source_root=RUNNING_ROOT)
    assert endpoint.time == .04 and endpoint.initial == cp.initial
    assert endpoint.metadata_json == cp.metadata_json
    assert np.array_equal(np.array(endpoint.state), states[-1])
    for grid in [[.01, .04], [0., 0.], [0., float('nan')]]:
        with pytest.raises(ValueError):
            evolve(cp, grid, source_root=RUNNING_ROOT)
    with pytest.raises(ValueError, match='running modules'):
        evolve(cp, [0., .04], source_root=tmp_path)
    damaged = cp.metadata; damaged['provenance']['sources'][0]['sha256'] = '0'*64
    changed = replace(cp, metadata_json=canonical_text(damaged))
    with pytest.raises(ValueError, match='source versions'):
        evolve(changed, [0., .04], source_root=RUNNING_ROOT)
    with pytest.raises(ValueError, match='SHA256'):
        verify_sources(changed, RUNNING_ROOT)
    outside = cp.metadata
    outside['provenance']['sources'].append(dict(path='../private.json', sha256='b'*64))
    with pytest.raises(ValueError, match='outside-root'):
        verify_sources(replace(cp, metadata_json=canonical_text(outside)), RUNNING_ROOT)
