"""Reproduce the pinned ten-body EIH-only year (protocol180)."""
import argparse
from dataclasses import asdict,replace
from importlib import import_module
import json
from pathlib import Path
import platform
from statistics import median
from time import perf_counter
import warnings

import numpy as np
import scipy

from scripts.eih_year import inputs,reference
from scripts.ias15_eih import ias_trajectory,dop_trajectory,invariant_drift
from scripts.assess_ias15_eih import initial_noether_check
from scripts.ias15_reference import load_library,library_hashes
from scripts.newton_year import ROOT,INPUTS,NAMES,LEVELS,DAY,hashes,errors,agreement
from scripts.assess_sandbox_planets import states
from solar_simulator.experiment import create_experiment,copy_bodies


def within(error,position,velocity):
    return error['position_metres']<position and error['velocity_m_per_s']<velocity


def reference_gate(row):
    return within(row['all_bodies'],1.,1e-6) and within(row['moon_relative_to_earth'],.01,1e-7)


def metrics(values,expected,seed,reference_passed):
    names = [b.name for b in seed.bodies]
    per_body = {name:errors(values[:,i],expected[:,i]) for i,name in enumerate(names)}
    row = agreement(values,expected,names)
    noether = invariant_drift(values,np.array([b.mass for b in seed.bodies]))
    numerical = all(within(e,10.,1e-4) for e in per_body.values()) and within(row['moon_relative_to_earth'],.1,1e-5)
    return dict(**row,per_body=per_body,noether_drift=noether,numerical_targets_passed=bool(numerical),
        checks_passed=bool(reference_passed and numerical and max(noether.values())<1e-10))


def run(output,directory,*,pilot=False):
    seed,times = inputs()
    if pilot:times = np.unique(np.r_[times[times<30*DAY],30*DAY])
    output = Path(output)
    if output.with_suffix('.json').exists() or output.with_suffix('.npz').exists():
        raise ValueError('Use a fresh output path; preserve previous audits')
    output.parent.mkdir(parents=True,exist_ok=True)
    library = load_library(directory)
    lib_before = library_hashes(library)
    native_paths = [Path(import_module(name).__file__) for name in ('solar_native','solar_native.solar_native')]
    native_before = hashes(native_paths)
    root = Path(library.__file__).resolve().parent.parent
    loaded = Path(library.clibrebound._name).resolve()
    if not loaded.is_relative_to(root) or hashes([loaded])[str(loaded)]!=lib_before[loaded.relative_to(root).as_posix()]:
        raise RuntimeError('Loaded REBOUND binary not in provenance')
    source_paths = [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    source_paths += ['scripts/eih_year.py','scripts/assess_eih_year.py','scripts/ias15_eih.py',
        'scripts/assess_ias15_eih.py','scripts/ias15_reference.py','scripts/newton_year.py',
        'scripts/assess_relativity.py','scripts/assess_sandbox_planets.py','docs/eih-year-protocol.md']
    source_before = hashes(source_paths)
    initial_check = initial_noether_check(seed)
    masses = np.array([b.mass for b in seed.bodies])
    document = dict(protocol='180',pilot=pilot,physics='full order-reduced harmonic EIH 1PN, no figures',
        origin=asdict(seed.origin),settings=asdict(seed.settings),names=list(NAMES),masses_kg=masses.tolist(),
        samples=len(times),duration_seconds=float(times[-1]),initial_noether=initial_check,
        inputs_sha256=INPUTS,source_sha256=source_before,library_sha256=lib_before,native_sha256=native_before,
        environment=dict(python=platform.python_version(),platform=platform.platform(),
            numpy=np.__version__,scipy=scipy.__version__,rebound=library.__version__),
        reference_levels=[],candidates={},cost={},complete=False)
    arrays = dict(times=times,initial=states(seed.bodies))
    def save():
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        document['npz_sha256'] = hashes([output.with_suffix('.npz').resolve()]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(document,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for i,(rtol,maximum,clock) in enumerate(LEVELS):
            start = perf_counter()
            values,metadata = reference(seed,times,rtol,maximum,clock)
            metadata['elapsed_seconds'] = perf_counter()-start
            metadata['initial_roundtrip'] = agreement(values[:1],arrays['initial'][None],list(NAMES))
            metadata['noether_drift'] = invariant_drift(values,masses)
            arrays['reference_'+str(i)] = values
            document['reference_levels'].append(metadata)
            save()
            print('reference',i,metadata,flush=True)
        comparisons = {str(i-1)+'_to_'+str(i):agreement(arrays['reference_'+str(i-1)],
            arrays['reference_'+str(i)],list(NAMES)) for i in (1,2,3)}
        ref_ok = (all(reference_gate(comparisons[key]) for key in ('1_to_2','2_to_3'))
            and all(within(row['initial_roundtrip']['all_bodies'],.002,1e-8)
                and row['initial_roundtrip']['moon_relative_to_earth']['position_metres']<.0001
                for row in document['reference_levels']))
        document['reference_comparisons'] = comparisons
        document['reference_passed'] = ref_ok
        print('reference_passed',ref_ok,comparisons,flush=True)
        tight = create_experiment(copy_bodies(seed.bodies),replace(seed.settings,
            position_atol=1e-7,velocity_atol=1e-13),origin=seed.origin)
        functions = {'dop853_baseline':lambda:dop_trajectory(seed,times),
            'dop853_tight':lambda:dop_trajectory(tight,times),
            'ias15_1e-9':lambda:ias_trajectory(seed,times,library,1e-9),
            'ias15_1e-11':lambda:ias_trajectory(seed,times,library,1e-11)}
        boundaries = None
        for name,function in functions.items():
            values,stats = function()
            np.testing.assert_array_equal(values[0],arrays['initial'])
            repeat,_ = function()
            np.testing.assert_array_equal(values,repeat)
            if boundaries is None:boundaries = stats['packet_endpoints']
            if stats['packet_endpoints']!=boundaries:raise RuntimeError('Different packet endpoints')
            arrays[name] = values
            row = metrics(values,arrays['reference_2'],seed,ref_ok and initial_check['checks_passed'])
            row.update(statistics=stats,repeat_bitexact=True)
            document['candidates'][name] = row
            save()
            print(name,row['all_bodies'],row['moon_relative_to_earth'],row['noether_drift'],row['checks_passed'],flush=True)
        document['packet_endpoints_equal'] = True
        document['packets'] = len(boundaries)
        if not pilot:
            durations = {name:[] for name in functions}
            for iteration in range(3):
                for name in (list(functions) if iteration%2==0 else list(reversed(functions))):
                    start = perf_counter()
                    values,_ = functions[name]()
                    elapsed = perf_counter()-start
                    np.testing.assert_array_equal(values,arrays[name])
                    durations[name].append(elapsed)
                print('timing round',iteration+1,flush=True)
            document['cost'] = {name:dict(seconds=rows,median_seconds=median(rows)) for name,rows in durations.items()}
        document['warnings'] = [str(w.message) for w in caught]
    if (hashes(source_paths)!=source_before or hashes(INPUTS)!=INPUTS or library_hashes(library)!=lib_before
            or hashes(native_paths)!=native_before):
        raise RuntimeError('Source/input/actual binary changed during integration')
    document['source_input_library_native_unchanged'] = True
    document['complete'] = True
    document['general_release'] = False
    document['checks_passed'] = bool(ref_ok and initial_check['checks_passed']
        and all(row['checks_passed'] for row in document['candidates'].values()))
    save()
    print('complete',output,'checks_passed',document['checks_passed'],flush=True)
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--library-directory',type=Path,required=True)
    parser.add_argument('--pilot',action='store_true')
    args = parser.parse_args()
    run(args.output,args.library_directory,pilot=args.pilot)


if __name__=='__main__':
    main()
