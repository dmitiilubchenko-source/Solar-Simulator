"""Reproduce protocol187 without modifying application settings or datasets."""
import argparse
from datetime import datetime,timezone
from importlib import import_module
import json
from pathlib import Path
import platform
from dataclasses import replace
from statistics import median
from time import perf_counter
import warnings

import numpy as np
import scipy

from scripts.fixed_j2_year import inputs,within,jpl_vectors,verify,INPUTS
from scripts.fixed_j2_ias import ias_trajectory,dop_trajectory
from scripts.ias15_reference import load_library,library_hashes
from scripts.newton_year import ROOT,NAMES,hashes,errors,agreement
from scripts.assess_sandbox_planets import states
from scripts.assess_dense_jpl import residuals
from solar_simulator.experiment import create_experiment,copy_bodies


def metrics(values,reference,reference_passed):
    if values.shape!=reference.shape or not np.isfinite(values).all():
        raise ValueError('Invalid candidate shape/nonfinite values')
    row = agreement(values,reference,list(NAMES))
    per_body = {name:errors(values[:,i],reference[:,i]) for i,name in enumerate(NAMES)}
    numerical = (all(within(e,10.,1e-4) for e in per_body.values())
        and within(row['moon_relative_to_earth'],.1,1e-5))
    return dict(**row,per_body=per_body,numerical_targets_passed=bool(numerical),
        checks_passed=bool(reference_passed and numerical))


def run(output,directory,raw_directory):
    output = Path(output).resolve()
    if output.with_suffix('.json').exists() or output.with_suffix('.npz').exists():
        raise ValueError('Use a new output path; preserve earlier audits')
    output.parent.mkdir(parents=True,exist_ok=True)
    seed,times,reference,old_baseline,preflight = inputs()
    library = load_library(directory)
    lib_before = library_hashes(library)
    root = Path(library.__file__).resolve().parent.parent
    loaded = Path(library.clibrebound._name).resolve()
    if (not loaded.is_relative_to(root)
            or hashes([loaded])[str(loaded)]!=lib_before[loaded.relative_to(root).as_posix()]):
        raise RuntimeError('Loaded REBOUND binary not in provenance')
    native_paths = [Path(import_module(n).__file__) for n in ('solar_native','solar_native.solar_native')]
    native_before = hashes(native_paths)
    if native_before[str(native_paths[1])]!='19327a3e4ff91d22ba7f6c181c0f37f4a134b16cb5d441cbc899a220d4e310f7':
        raise RuntimeError('Actual native binary differs from qualified build')
    source_paths = [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    source_paths += ['scripts/'+n+'.py' for n in ('assess_fixed_j2_year','fixed_j2_year',
        'fixed_j2_ias','eih_year','ias15_eih','newton_year','ias15_reference',
        'assess_sandbox_planets','assess_dense_jpl','fetch_ephemerides')]
    source_paths += ['docs/fixed-j2-year-protocol.md']
    # Bind the implementation of SciPy as well as its version string.
    import scipy.integrate._ivp.rk as rk
    import scipy.integrate._ivp.base as base
    scipy_paths = [Path(rk.__file__),Path(base.__file__)]
    source_before = hashes(source_paths)
    scipy_before = hashes(scipy_paths)
    document = dict(protocol='docs/fixed-j2-year-protocol.md',
        started_utc=datetime.now(timezone.utc).isoformat(),preflight=preflight,
        inputs_sha256=INPUTS,source_sha256=source_before,library_sha256=lib_before,
        native_sha256=native_before,scipy_source_sha256=scipy_before,
        environment=dict(python=platform.python_version(),platform=platform.platform(),
            numpy=np.__version__,scipy=scipy.__version__,rebound=library.__version__),
        samples=len(times),duration_seconds=float(times[-1]),candidates={},cost={},
        annual_source_integrals_verified=False,general_release=False,complete=False)
    arrays = dict(times=times,initial=states(seed.bodies),reference=reference)
    def save():
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        document['npz_sha256'] = hashes([output.with_suffix('.npz')]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(document,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save()
    try:
        tight = create_experiment(copy_bodies(seed.bodies),replace(seed.settings,
            position_atol=1e-7,velocity_atol=1e-13),origin=seed.origin)
        functions = {'dop853_baseline':lambda:dop_trajectory(seed,times),
            'dop853_tight':lambda:dop_trajectory(tight,times),
            'ias15_1e-9':lambda:ias_trajectory(seed,times,library,1e-9),
            'ias15_1e-11':lambda:ias_trajectory(seed,times,library,1e-11)}
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            boundaries = None
            for name,function in functions.items():
                values,stats = function()
                arrays[name] = values
                save()
                np.testing.assert_array_equal(values[0],arrays['initial'])
                if name=='dop853_baseline':
                    np.testing.assert_array_equal(values,old_baseline)
                    document['old_baseline_bitexact'] = True
                repeat,repeat_stats = function()
                np.testing.assert_array_equal(values,repeat)
                if boundaries is None:boundaries = stats['packet_endpoints']
                if (stats['packet_endpoints']!=boundaries or repeat_stats['packet_endpoints']!=boundaries
                        or len(boundaries)!=499 or boundaries[-1]!=times[-1]
                        or not set(times[1:]).issubset(boundaries)
                        or not np.all(np.diff(boundaries)>0) or stats.get('failed',False)):
                    raise RuntimeError('Candidate did not finish the common exact packet grid')
                row = metrics(values,reference,preflight['checks_passed'])
                row.update(statistics=stats,repeat_bitexact=True)
                document['candidates'][name] = row
                save()
                print(name,row['all_bodies'],row['moon_relative_to_earth'],
                    'numerical',row['checks_passed'],flush=True)
            document['packet_endpoints_equal'] = True
            document['packets'] = len(boundaries)
            durations = {name:[] for name in functions}
            for iteration in range(3):
                order = list(functions) if iteration%2==0 else list(reversed(functions))
                for name in order:
                    start = perf_counter()
                    values,stats = functions[name]()
                    elapsed = perf_counter()-start
                    np.testing.assert_array_equal(values,arrays[name])
                    if stats['packet_endpoints']!=boundaries:raise RuntimeError('Timed packet grid differs')
                    durations[name].append(elapsed)
                print('timing round',iteration+1,flush=True)
            document['cost'] = {name:dict(seconds=rows,median_seconds=median(rows))
                for name,rows in durations.items()}
            # No JPL state is read by a candidate or used to choose its parameters.
            expected,epochs,raw_hashes = jpl_vectors(seed,times,raw_directory)
            arrays['jpl'] = expected
            document['jpl_raw_sha256'] = raw_hashes
            document['jpl_loaded_after_free_integration'] = True
            for name in functions:
                document['candidates'][name].update(residuals(arrays[name],expected,list(NAMES),epochs))
            document['warnings'] = [str(w.message) for w in caught]
        verify(INPUTS)
        if (hashes(source_paths)!=source_before or library_hashes(library)!=lib_before
                or hashes(native_paths)!=native_before or hashes(scipy_paths)!=scipy_before
                or hashes(raw_hashes)!=raw_hashes):
            raise RuntimeError('Source/input/library/actual binary/raw data changed')
        # Revalidate the model/profile/IC contract after all timed calls as well.
        inputs()
        document['source_input_library_native_unchanged'] = True
        document['complete'] = True
        document['checks_passed'] = all(row['checks_passed'] and row['physical_goals_passed']
            for row in document['candidates'].values())
        save()
    except Exception as error:
        document['failure'] = dict(type=type(error).__name__,message=str(error))
        save()
        raise
    print('complete',output,'checks_passed',document['checks_passed'],flush=True)
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--library-directory',type=Path,required=True)
    parser.add_argument('--raw-cache',type=Path,required=True)
    args = parser.parse_args()
    if not run(args.output,args.library_directory,args.raw_cache)['checks_passed']:
        raise RuntimeError('Declared year criteria failed; report preserved')


if __name__=='__main__':main()
