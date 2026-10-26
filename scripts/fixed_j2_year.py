"""Qualified public EIH+fixed-J2 year cache; no integration or fitting here."""
from dataclasses import asdict,replace
import hashlib
import json
from pathlib import Path

import numpy as np

from scripts.fixed_j2_ias import validate
from scripts.newton_year import ROOT,NAMES,YEAR,INPUTS as BASE_INPUTS,agreement
from scripts.assess_sandbox_planets import states
from solar_simulator.application_profiles import solar_sandbox
from solar_simulator.storage import load

INPUTS = dict(BASE_INPUTS,**{
    'docs/continuous-integration-validation.json':'043164cf12c2271f4ba29ac345b82eb2cb7cf3e2453641e3212b66abab85b871',
    'docs/strict-profile-validation.json':'bcd4fb6ae800ee88962d3a988a9e8944e2a692dc7a5a0a80cfffae865e9db172',
    'docs/qualification-grid-validation.json':'ad95ca2e1012fc7778232430b993133ead4d2e62548a38275559af239660d0b0',
    'docs/qualification-grid-reference.json':'f565c3d12394c6def8cc594ff614415ba8f05495bd89a1ac4b9dbc81c4609cbe',
    'docs/dense-jpl-validation.json':'fb6a38baa0fff419e1c67c48447b3b385602a84274a93d560f5f1c92f3ebb3cc',
})


def verify(bindings,root=ROOT, *, historical=False):
    """Bind exact bytes; all relative receipt paths must stay inside the repo."""
    if historical:
        from scripts.assess_nominal_jpl import verify_frozen_sources
        verify_frozen_sources(bindings, root=root)
        return
    root = Path(root).resolve()
    for name,expected in bindings.items():
        path = (root/name).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Receipt path outside project: '+name)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            raise ValueError('SHA mismatch: '+name)


def canonical(value):
    return json.loads(json.dumps(value))


def within(error,position,velocity):
    return error['position_metres']<position and error['velocity_m_per_s']<velocity


def validate_payload(seed,times,reference,baseline,year,strict,prior):
    """Reject mismatched models even when their trajectory shapes agree."""
    validate(seed,times)
    settings = canonical(asdict(seed.settings))
    origin = asdict(seed.origin)
    if (settings!=year['settings'] or settings!=strict['settings']
            or origin!=year['origin'] or origin!=strict['origin'] or origin!=prior['origin']
            or settings['physics']!='eih-1pn' or len(settings['figures'])!=2
            or [f['body'] for f in settings['figures']]!=['Sun','Earth']
            or tuple(b.name for b in seed.bodies)!=NAMES):
        raise ValueError('Model/settings/origin/body order mismatch')
    # The old reference used a different numerical production tolerance/backend.
    # Physical and coordinate settings, rather than that production control, bind it.
    for key in ('physics','figures','relative_pair','error_control','dt'):
        if prior['settings'][key]!=settings[key]:
            raise ValueError('Reference physical settings mismatch: '+key)
    grid = (np.array(prior['epochs_jd_tdb'])-origin['epoch_jd_tdb'])*86400
    if len(times)!=125 or times[-1]!=YEAR or not np.array_equal(times,grid):
        raise ValueError('Reference epoch grid mismatch')
    shape = (125,len(NAMES),6)
    if (reference.shape!=shape or baseline.shape!=shape
            or not np.isfinite(reference).all() or not np.isfinite(baseline).all()):
        raise ValueError('Reference shape/nonfinite values')
    if not np.array_equal(baseline[0],states(seed.bodies)):
        raise ValueError('Checkpoint initial states mismatch')
    profile = solar_sandbox(backend='rust')
    if (replace(profile.settings,rtol=3e-14)!=seed.settings or profile.origin!=seed.origin
            or [b.mass for b in profile.bodies]!=[b.mass for b in seed.bodies]
            or not np.array_equal(states(profile.bodies),states(seed.bodies))):
        raise ValueError('Checkpoint/profile IC/masses mismatch')
    initial = agreement(reference[:1],baseline[:1],list(NAMES))
    if (not within(initial['all_bodies'],.002,1e-8)
            or initial['moon_relative_to_earth']['position_metres']>=.0001):
        raise ValueError('Reference initial roundtrip failed')
    sensitivity = prior['reference_convergence']
    if sensitivity!=year['reference_uncertainty']:
        raise ValueError('Reference sensitivity lineage mismatch')
    for key,p,v in (('all_bodies',1.,1e-6),('moon_relative_to_earth',.01,1e-7)):
        row = sensitivity[key]
        if not (0<=row['maximum_position_metres']<p and 0<=row['maximum_velocity_m_per_s']<v):
            raise ValueError('Reference sensitivity failed')
    return dict(initial_roundtrip=initial,refinement_sensitivity=sensitivity,
        source_integrals_available=False,checks_passed=True)


def inputs(root=ROOT):
    root = Path(root)
    verify(INPUTS,root)
    read = lambda name:json.loads((root/'docs'/name).read_bytes())
    continuous = read('continuous-integration-validation.json')
    strict = read('strict-profile-validation.json')
    prior = read('qualification-grid-validation.json')
    for receipt in (continuous,strict,prior):verify(receipt['source_sha256'],root,historical=True)
    verify({'docs/qualification-grid-validation.json':strict['before_report_sha256'],
        'docs/solar-sandbox-strict-checkpoint.json':strict['checkpoint_sha256'],
        'docs/continuous-integration-reference.npz':continuous['public_reference_sha256']},root)
    year = continuous['outcomes']['year']
    if year['reference_cache_sha256']!=strict['cache_sha256']:
        raise ValueError('Historical cache lineage mismatch')
    seed = load(root/'docs/solar-sandbox-strict-checkpoint.json')
    with np.load(root/'docs/continuous-integration-reference.npz',allow_pickle=False) as data:
        times,reference,baseline = [data[k].copy() for k in
            ('year_times','year_independent','year_continuous')]
    metadata = validate_payload(seed,times,reference,baseline,year,strict,prior)
    metadata.update(inputs_sha256=INPUTS,origin=asdict(seed.origin),settings=asdict(seed.settings),
        names=list(NAMES),masses_kg=[b.mass for b in seed.bodies])
    return seed,times,reference,baseline,metadata


def historical_lineage(root=ROOT):
    """Optional local deep proof; public reproduction does not require .tools."""
    seed,times,reference,_,metadata = inputs(root)
    root = Path(root)
    strict = json.loads((root/'docs/strict-profile-validation.json').read_bytes())
    prior = json.loads((root/'docs/qualification-grid-validation.json').read_bytes())
    production = '.tools/qualification138/production139.npz'
    raw = '.tools/qualification138/reference139.npz'
    bindings = {production:strict['cache_sha256'],raw:prior['reference_sha256'][raw]}
    verify(bindings,root)
    with np.load(root/production,allow_pickle=False) as a,np.load(root/raw,allow_pickle=False) as b:
        for actual,expected in ((a['times'],times),(b['times'],times),
                (a['reference'],reference),(b['level_1'],reference),
                (a['rust_tighter'][0],states(seed.bodies))):
            np.testing.assert_array_equal(actual,expected)
        # Recompute the published sensitivity, rather than merely trusting its label.
        measured = agreement(b['level_0'],b['level_1'],list(NAMES))
        for key,row in metadata['refinement_sensitivity'].items():
            if (measured[key]['position_metres']!=row['maximum_position_metres']
                    or measured[key]['velocity_m_per_s']!=row['maximum_velocity_m_per_s']):
                raise ValueError('Historical refinement values differ')
    return dict(**metadata,historical_sha256=bindings,public_raw_reference_bitexact=True)


def jpl_vectors(seed,times,raw_directory,root=ROOT):
    """Read only after free trajectories; reparse every pinned raw JPL response."""
    from scripts.assess_dense_jpl import validate_reference
    from scripts.fetch_ephemerides import parse_result
    from solar_simulator.ephemerides import RESOLVED_IDS
    root = Path(root)
    verify(INPUTS,root)
    dense = json.loads((root/'docs/qualification-grid-reference.json').read_bytes())
    receipt = json.loads((root/'docs/dense-jpl-validation.json').read_bytes())
    verify(dense['source_sha256'],root)
    verify(receipt['source_sha256'],root)
    grid = dense['epochs_jd_tdb']
    if not np.array_equal((np.array(grid)-seed.origin.epoch_jd_tdb)*86400,times):
        raise ValueError('JPL time grid mismatch')
    expected = validate_reference(dense,seed.origin,list(NAMES),RESOLVED_IDS,grid)
    raw_hashes = {}
    for body in dense['bodies']:
        rows,offset = [],0
        for request in body['requests']:
            path = Path(raw_directory)/f"horizons-{body['id']}-{offset:03d}.json"
            payload = path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            if digest!=request['response_sha256']:raise ValueError('Raw JPL SHA mismatch')
            raw_hashes[str(path)] = digest
            rows.extend(parse_result(json.loads(payload),body['id'],request['epochs_jd_tdb']))
            offset += len(request['epochs_jd_tdb'])
        if rows!=body['states']:raise ValueError('JPL vectors differ from original parser')
    if len(raw_hashes)!=40:raise ValueError('Expected 40 distinct JPL batches')
    return expected,grid,raw_hashes
