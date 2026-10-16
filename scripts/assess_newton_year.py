"""Reproduce protocol171 without changing application settings or data."""
import argparse
from dataclasses import asdict, replace
from importlib import import_module
import json
import platform
from pathlib import Path
from statistics import median
from time import perf_counter
import warnings

import numpy as np
import scipy

from scripts.ias15_reference import load_library, library_hashes
from scripts.newton_year import (ROOT, DAY, YEAR, LEVELS, INPUTS, NAMES, hashes, inputs,
    reference, dop_trajectory, ias_trajectory, agreement, errors, invariants)
from scripts.assess_sandbox_planets import states
from solar_simulator.experiment import create_experiment, copy_bodies


def bounded(row,position,velocity):
    return row['position_metres']<position and row['velocity_m_per_s']<velocity


def reference_gate(row):
    return bounded(row['all_bodies'],1.,1e-6) and bounded(row['moon_relative_to_earth'],.01,1e-7)


def candidate_metrics(values,expected,seed,reference_passed):
    names = [b.name for b in seed.bodies]
    per_body = {name:errors(values[:,i],expected[:,i]) for i,name in enumerate(names)}
    row = agreement(values,expected,names)
    inv = invariants(values,np.array([b.mass for b in seed.bodies]))
    numerical = (all(bounded(b,10.,1e-4) for b in per_body.values())
        and bounded(row['moon_relative_to_earth'],.1,1e-5))
    return dict(**row,per_body=per_body,invariants=inv,numerical_targets_passed=numerical,
        checks_passed=bool(reference_passed and numerical and max(inv.values())<1e-10))


def run(output,library_directory,*,pilot=False):
    seed,times = inputs()
    if pilot:
        times = np.unique(np.r_[times[times<30*DAY],30*DAY])
    library = load_library(library_directory)
    source_paths = [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    source_paths += ['scripts/newton_year.py','scripts/assess_newton_year.py',
        'scripts/ias15_reference.py','scripts/assess_sandbox_planets.py','docs/newton-year-protocol.md']
    source_before,library_before = hashes(source_paths),library_hashes(library)
    native = __import__('solar_native')
    native_paths = [Path(native.__file__),Path(import_module('solar_native.solar_native').__file__)]
    native_before = hashes(native_paths)
    loaded = Path(library.clibrebound._name).resolve()
    library_root = Path(library.__file__).resolve().parent.parent
    if (not loaded.is_relative_to(library_root)
            or hashes([loaded])[str(loaded)]!=library_before[loaded.relative_to(library_root).as_posix()]):
        raise RuntimeError('Loaded REBOUND binary does not match recorded library files')
    output = Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    if output.with_suffix('.json').exists() or output.with_suffix('.npz').exists():
        raise ValueError('Use a fresh output path; do not overwrite a previous audit')
    report = dict(protocol='171',pilot=pilot,physics='newtonian point masses',
        origin=asdict(seed.origin),settings=asdict(seed.settings),names=list(NAMES),
        masses_kg=[b.mass for b in seed.bodies],G_SI=__import__('solar_simulator.simulation',fromlist=['G']).G,
        samples=len(times),duration_seconds=float(times[-1]),inputs_sha256=INPUTS,
        source_sha256=source_before,library_sha256=library_before,native_sha256=native_before,
        environment=dict(python=platform.python_version(),platform=platform.platform(),
            numpy=np.__version__,scipy=scipy.__version__,rebound=library.__version__),
        reference_levels=[],candidates={},cost={},warnings=[],complete=False)
    arrays = dict(times=times,initial=states(seed.bodies))
    def save():
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        report['npz_sha256'] = hashes([output.with_suffix('.npz').resolve()]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for i,(rtol,maximum,clock) in enumerate(LEVELS):
            start = perf_counter()
            values,metadata = reference(seed,times,rtol,maximum,clock)
            metadata['elapsed_seconds'] = perf_counter()-start
            metadata['initial_roundtrip'] = agreement(values[:1],arrays['initial'][None],list(NAMES))
            arrays['reference_'+str(i)] = values
            report['reference_levels'].append(metadata)
            save()
            print('reference',i,metadata,flush=True)
        comparisons = {str(i-1)+'_to_'+str(i):agreement(arrays['reference_'+str(i-1)],
            arrays['reference_'+str(i)],list(NAMES)) for i in (1,2,3)}
        roundtrips = [row['initial_roundtrip'] for row in report['reference_levels']]
        reference_passed = (all(reference_gate(comparisons[key]) for key in ('1_to_2','2_to_3'))
            and all(bounded(row['all_bodies'],.002,1e-8)
                and row['moon_relative_to_earth']['position_metres']<.0001 for row in roundtrips))
        report['reference_comparisons'] = comparisons
        report['reference_passed'] = reference_passed
        print('reference_passed',reference_passed,comparisons,flush=True)
        tight = create_experiment(copy_bodies(seed.bodies),replace(seed.settings,
            position_atol=1e-7,velocity_atol=1e-13),origin=seed.origin)
        functions = {
            'dop853_baseline':lambda:dop_trajectory(seed,times),
            'dop853_tight':lambda:dop_trajectory(tight,times),
            'ias15_1e-9':lambda:ias_trajectory(seed,times,library,1e-9),
            'ias15_1e-11':lambda:ias_trajectory(seed,times,library,1e-11),
        }
        packet_bounds = None
        for name,function in functions.items():
            values,metadata = function()
            np.testing.assert_array_equal(values[0],arrays['initial'])
            arrays[name] = values
            if packet_bounds is None:
                packet_bounds = metadata['packet_endpoints']
            if metadata['packet_endpoints']!=packet_bounds:
                raise ValueError('Different packet endpoints')
            row = candidate_metrics(values,arrays['reference_2'],seed,reference_passed)
            row['statistics'] = metadata
            repeat,_ = function()
            np.testing.assert_array_equal(values,repeat)
            row['repeat_bitexact'] = True
            if name.startswith('ias15'):
                counted,stats = ias_trajectory(seed,times,library,float(name.split('_')[1]),count_forces=True)
                np.testing.assert_array_equal(values,counted)
                row['counter_bitexact'] = True
                row['statistics']['force_evaluations'] = stats['force_evaluations']
            report['candidates'][name] = row
            save()
            print(name,row['all_bodies'],row['moon_relative_to_earth'],row['checks_passed'],flush=True)
        report['packet_endpoints_equal'] = True
        report['packets'] = len(packet_bounds)
        if not pilot:
            # Untimed first/repeat runs above also warm all candidate paths.
            durations = {name:[] for name in functions}
            for repetition in range(3):
                order = list(functions) if repetition%2==0 else list(reversed(functions))
                for name in order:
                    start = perf_counter()
                    values,_ = functions[name]()
                    elapsed = perf_counter()-start
                    np.testing.assert_array_equal(values,arrays[name])
                    durations[name].append(elapsed)
                print('timing round',repetition+1,flush=True)
            report['cost'] = {name:dict(seconds=rows,median_seconds=median(rows))
                for name,rows in durations.items()}
        report['warnings'] = [str(w.message) for w in caught]
    if hashes(source_paths)!=source_before or library_hashes(library)!=library_before:
        raise RuntimeError('Source or REBOUND changed during integration')
    if hashes(INPUTS)!=INPUTS or hashes(native_paths)!=native_before:
        raise RuntimeError('Input or native binary changed during integration')
    report['source_input_library_unchanged'] = True
    report['complete'] = True
    report['general_release'] = False
    report['checks_passed'] = bool(reference_passed and all(r['checks_passed'] for r in report['candidates'].values()))
    save()
    print('complete',output,'checks_passed',report['checks_passed'],flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--library-directory',type=Path,required=True)
    parser.add_argument('--pilot',action='store_true')
    args = parser.parse_args()
    run(args.output,args.library_directory,pilot=args.pilot)


if __name__=='__main__':
    main()
