"""Model-matched IAS15/EIH feasibility, protocol177, entirely outside runtime."""
import argparse
from importlib import import_module
import json
from pathlib import Path
from statistics import median
from time import perf_counter
import warnings

import numpy as np
import scipy

from scripts.ias15_eih import (circle,triple,drag_probe,ias_trajectory,dop_trajectory,
    independent_reference,noether,invariant_drift)
from scripts.ias15_reference import load_library,library_hashes
from scripts.newton_year import ROOT,YEAR,DAY,hashes,errors,invariants as newton_drift
from scripts.assess_sandbox_planets import states
from solar_simulator.native_forces import prepare
from solar_simulator.relativity import invariants


def within(error,position,velocity):
    return error['position_metres']<position and error['velocity_m_per_s']<velocity


def initial_noether_check(seed):
    q = states(seed.bodies)
    masses = np.array([b.mass for b in seed.bodies])
    independent = noether(q,masses)
    energy,p,l = invariants(seed.bodies)
    runtime = np.r_[energy,[p.x,p.y,p.z],[l.x,l.y,l.z]]
    pscale = sum(m*np.linalg.norm(v) for m,v in zip(masses,q[:,3:]))
    scale = np.r_[abs(energy),[pscale]*3,[np.linalg.norm(runtime[4:])]*3]
    maximum = float(np.max(abs(independent-runtime)/scale))
    return dict(maximum_scaled_difference=maximum,checks_passed=maximum<5e-14)


def run(output,directory):
    output = Path(output)
    if output.with_suffix('.json').exists() or output.with_suffix('.npz').exists():
        raise ValueError('Use a fresh output path')
    output.parent.mkdir(parents=True,exist_ok=True)
    source_paths = [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    source_paths += ['scripts/ias15_eih.py','scripts/assess_ias15_eih.py',
        'scripts/ias15_reference.py','scripts/newton_year.py','scripts/assess_relativity.py',
        'scripts/assess_sandbox_planets.py','docs/ias15-eih-protocol.md']
    before = hashes(source_paths)
    library = load_library(directory)
    lib_before = library_hashes(library)
    native_paths = [Path(import_module(name).__file__) for name in ('solar_native','solar_native.solar_native')]
    native_before = hashes(native_paths)
    loaded = Path(library.clibrebound._name).resolve()
    libroot = Path(library.__file__).resolve().parent.parent
    if not loaded.is_relative_to(libroot) or hashes([loaded])[str(loaded)]!=lib_before[loaded.relative_to(libroot).as_posix()]:
        raise RuntimeError('Loaded REBOUND binary not in provenance')
    document = dict(protocol='177',source_sha256=before,library_sha256=lib_before,
        native_sha256=native_before,environment=dict(numpy=np.__version__,scipy=scipy.__version__,
            rebound=library.__version__),api={},reference_levels=[],cases={},complete=False)
    arrays = {}
    def save():
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        document['npz_sha256'] = hashes([output.with_suffix('.npz').resolve()]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(document,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for flag in (True,False):
            values,expected,stats = drag_probe(library,flag)
            error = errors(values,expected)
            document['api'][str(flag)] = dict(error=error,statistics=stats,
                matches_analytic=within(error,.001,1e-6))
            arrays['drag_'+str(flag)] = values
            arrays['drag_expected'] = expected
        document['api_passed'] = document['api']['True']['matches_analytic'] and not document['api']['False']['matches_analytic']
        save()
        print('API',document['api'],flush=True)
        circle_seed,circle_times,expected_circle,details = circle()
        triple_seed,triple_times = triple()
        levels = ((1e-13,1800.,YEAR),(3e-14,900.,YEAR),(3e-14,450.,YEAR),(3e-14,450.,DAY))
        for i,(rtol,maximum,clock) in enumerate(levels):
            start = perf_counter()
            values,metadata = independent_reference(triple_seed,triple_times,rtol,maximum,clock)
            metadata['seconds'] = perf_counter()-start
            metadata['noether_drift'] = invariant_drift(values,np.array([b.mass for b in triple_seed.bodies]))
            arrays['triple_reference_'+str(i)] = values
            document['reference_levels'].append(metadata)
            save()
            print('reference',i,metadata,flush=True)
        comparisons = {str(i-1)+'_to_'+str(i):errors(arrays['triple_reference_'+str(i-1)],
            arrays['triple_reference_'+str(i)]) for i in (1,2,3)}
        ref_ok = (all(within(comparisons[key],.1,1e-6) for key in ('1_to_2','2_to_3'))
            and all(within(row['initial_roundtrip'],.002,1e-8) for row in document['reference_levels']))
        document['reference_comparisons'] = comparisons
        document['reference_passed'] = ref_ok
        print('reference_passed',ref_ok,comparisons,flush=True)
        native_circle = prepare(np.array([b.mass for b in circle_seed.bodies]))
        wrong,wrong_stats = ias_trajectory(circle_seed,circle_times,library,1e-9,
            acceleration=lambda p,v:native_circle(p,v))
        arrays['circle_newton_negative'] = wrong
        document['newton_negative_control'] = dict(error=errors(wrong,expected_circle),statistics=wrong_stats)
        document['newton_negative_control']['failed_eih_targets'] = not within(errors(wrong,expected_circle),.1,1e-4)
        cases = [('circle',circle_seed,circle_times,expected_circle,True,.1,1e-4),
            ('triple',triple_seed,triple_times,arrays['triple_reference_2'],ref_ok,1.,1e-5)]
        for name,seed,times,expected,reference_passed,position_gate,velocity_gate in cases:
            masses = np.array([b.mass for b in seed.bodies])
            arrays[name+'_times'],arrays[name+'_initial'],arrays[name+'_expected'] = times,states(seed.bodies),expected
            row = dict(samples=len(times),duration_seconds=float(times[-1]),initial_noether=initial_noether_check(seed),
                initial_state_sha256=__import__('hashlib').sha256(states(seed.bodies).tobytes()).hexdigest(),
                masses_kg=masses.tolist(),candidates={})
            if name=='circle':row['analytic'] = details
            functions = {'dop853':lambda:dop_trajectory(seed,times),
                'ias15_1e-9':lambda:ias_trajectory(seed,times,library,1e-9),
                'ias15_1e-11':lambda:ias_trajectory(seed,times,library,1e-11)}
            boundaries = None
            for candidate,function in functions.items():
                values,stats = function()
                np.testing.assert_array_equal(values[0],states(seed.bodies))
                repeat,_ = function()
                np.testing.assert_array_equal(values,repeat)
                if boundaries is None:boundaries = stats['packet_endpoints']
                if stats['packet_endpoints']!=boundaries:raise RuntimeError('Different packet endpoints')
                arrays[name+'_'+candidate] = values
                error = errors(values,expected)
                drift = invariant_drift(values,masses)
                passed = bool(reference_passed and row['initial_noether']['checks_passed']
                    and within(error,position_gate,velocity_gate) and max(drift.values())<1e-10)
                row['candidates'][candidate] = dict(error=error,
                    per_body={str(i):errors(values[:,i],expected[:,i]) for i in range(len(masses))},
                    noether_drift=drift,newtonian_drift_diagnostic_only=newton_drift(values,masses),
                    statistics=stats,repeat_bitexact=True,checks_passed=passed)
                print(name,candidate,error,drift,'passed',passed,flush=True)
            row['packet_endpoints_equal'] = True
            row['packets'] = len(boundaries)
            durations = {candidate:[] for candidate in functions}
            for iteration in range(3):
                for candidate in (list(functions) if iteration%2==0 else list(reversed(functions))):
                    start = perf_counter()
                    values,_ = functions[candidate]()
                    elapsed = perf_counter()-start
                    np.testing.assert_array_equal(values,arrays[name+'_'+candidate])
                    durations[candidate].append(elapsed)
            row['cost'] = {candidate:dict(seconds=values,median_seconds=median(values)) for candidate,values in durations.items()}
            document['cases'][name] = row
            save()
        document['warnings'] = [str(w.message) for w in caught]
    if hashes(source_paths)!=before or library_hashes(library)!=lib_before or hashes(native_paths)!=native_before:
        raise RuntimeError('Source or actual binary changed during integration')
    document['source_library_native_unchanged'] = True
    document['complete'] = True
    document['general_release'] = False
    document['checks_passed'] = bool(ref_ok and document['api_passed']
        and document['newton_negative_control']['failed_eih_targets']
        and all(c['checks_passed'] for row in document['cases'].values() for c in row['candidates'].values()))
    save()
    print('complete',output,'checks_passed',document['checks_passed'],flush=True)
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--library-directory',type=Path,required=True)
    args = parser.parse_args()
    run(args.output,args.library_directory)


if __name__=='__main__':
    main()
