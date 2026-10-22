"""Narrow qualification of original RK45 caches; never certifies old runtime code."""
from dataclasses import asdict, replace
import json
from pathlib import Path

import numpy as np

from scripts.assess_newton_year import bounded, reference_gate
from scripts.assess_sandbox_planets import states
from scripts.ias15_restart import bits
from scripts.kepler_transport import ROOT, public_path, sha
from scripts.newton_year import DAY, G, INPUTS, LEVELS, NAMES, agreement, validate
from solar_simulator.experiment import copy_bodies, create_experiment
from solar_simulator.storage import load as load_checkpoint

RECEIPT = 'docs/newton-year-validation.json'
ARCHIVES = {p:'docs/native-newton-'+p+'-reference.npz' for p in ('pilot', 'year')}
RECEIPT_SHA = '0ea0baa2813978fa9606edf410b58c8389ad4f0598fe8daa54672cabf756b124'


def load(root=ROOT):
    root = Path(root).resolve()
    if sha(root/RECEIPT) != RECEIPT_SHA:
        raise ValueError('Changed original year receipt175')
    receipt = json.loads((root/RECEIPT).read_text(encoding='utf-8'))
    for name, expected in INPUTS.items():
        if sha(public_path(root, name)) != expected:
            raise ValueError('Changed year input: '+name)
    original = load_checkpoint(public_path(root, 'docs/solar-sandbox-strict-checkpoint.json'))
    seed = create_experiment(copy_bodies(original.bodies),
        replace(original.settings, physics='newtonian', figures=()), origin=original.origin)
    with np.load(public_path(root, 'docs/continuous-integration-reference.npz'), allow_pickle=False) as saved:
        year_times = saved['year_times'].copy()
    validate(seed, year_times)
    initial, masses = states(seed.bodies), [b.mass for b in seed.bodies]
    dependencies = ('scripts/newton_year.py', 'scripts/assess_newton_year.py',
                    'scripts/assess_sandbox_planets.py', 'src/solar_simulator/simulation.py')
    profiles, qualifications = {}, {}
    for profile, name in ARCHIVES.items():
        row = receipt[profile]
        path = public_path(root, name)
        if sha(path) != receipt['receipts'][profile+'175']['npz_sha256']:
            raise ValueError('Changed original RK45 cache: '+profile)
        for source in dependencies:
            if sha(public_path(root, source)) != row['source_sha256'][source]:
                raise ValueError('Changed RK45 reference dependency: '+source)
        for source, expected in INPUTS.items():
            if sha(public_path(root, source)) != expected:
                raise ValueError('Changed year input: '+source)
        with np.load(path, allow_pickle=False) as saved:
            data = {k:saved[k].copy() for k in saved.files}
        expected_times = np.unique(np.r_[year_times[year_times < 30*DAY], 30*DAY]) if profile == 'pilot' else year_times
        if (bits(data['initial']) != bits(initial) or bits(data['times']) != bits(expected_times)
                or bits(row['masses_kg']) != bits(masses) or row['G_SI'] != G
                or row['names'] != list(NAMES) or asdict(seed.origin) != row['origin']
                or json.loads(json.dumps(asdict(seed.settings))) != row['settings'] or not row['complete']
                or row['inputs_sha256'] != INPUTS or len(data['times']) != (61 if profile == 'pilot' else 125)):
            raise ValueError('Changed IC/grid/masses/model/origin in year cache')
        for i, level in enumerate(LEVELS):
            q = data['reference_'+str(i)]
            metadata = row['reference_levels'][i]
            if (q.shape != (len(expected_times), 10, 6) or not np.isfinite(q).all()
                    or tuple(metadata[k] for k in ('rtol', 'max_step_seconds', 'clock_seconds')) != level):
                raise ValueError('Invalid RK45 level shape/settings')
        comparisons = {str(i-1)+'_to_'+str(i):agreement(data['reference_'+str(i-1)],
                       data['reference_'+str(i)], list(NAMES)) for i in (1, 2, 3)}
        roundtrips = [agreement(data['reference_'+str(i)][:1], initial[None], list(NAMES)) for i in range(4)]
        passed = (all(reference_gate(comparisons[k]) for k in ('1_to_2', '2_to_3'))
                  and all(bounded(r['all_bodies'], .002, 1e-8)
                          and r['moon_relative_to_earth']['position_metres'] < .0001 for r in roundtrips))
        if (comparisons != row['reference_comparisons']
                or roundtrips != [r['initial_roundtrip'] for r in row['reference_levels']]
                or passed is not row['reference_passed'] or not passed):
            raise ValueError('RK45 sensitivity/roundtrip qualification failed')
        changed = [n for n, expected in row['source_sha256'].items() if sha(public_path(root, n)) != expected]
        profiles[profile] = data
        qualifications[profile] = dict(comparisons=comparisons, roundtrips=roundtrips, reference_passed=True,
            reference_dependencies={n:row['source_sha256'][n] for n in dependencies},
            historical_wide_source_changes=changed, historical_runtime_requalified=False)
    return seed, profiles, qualifications, receipt
