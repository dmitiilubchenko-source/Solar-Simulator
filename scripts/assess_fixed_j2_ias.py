"""FixedJ2 force/torque/truncation contract, model tasks only (protocol184)."""
import argparse
from dataclasses import asdict
from importlib import import_module
import json
from pathlib import Path
from statistics import median
from time import perf_counter
import warnings

import numpy as np
import scipy

from scripts.fixed_j2_ias import (model,entries,potential,figure_force,reference,
    ias_trajectory,dop_trajectory,balances,scales)
from scripts.ias15_reference import load_library,library_hashes
from scripts.newton_year import ROOT,hashes,errors
from scripts.assess_sandbox_planets import states
from scripts.ias15_eih import noether


def within(error,position,velocity):
    return error['position_metres']<position and error['velocity_m_per_s']<velocity


def run(output,directory):
    output = Path(output)
    if output.with_suffix('.json').exists() or output.with_suffix('.npz').exists():
        raise ValueError('Use a fresh output path')
    output.parent.mkdir(parents=True,exist_ok=True)
    library = load_library(directory);lib_before = library_hashes(library)
    native_paths = [Path(import_module(name).__file__) for name in ('solar_native','solar_native.solar_native')]
    native_before = hashes(native_paths)
    root = Path(library.__file__).resolve().parent.parent;loaded = Path(library.clibrebound._name).resolve()
    if not loaded.is_relative_to(root) or hashes([loaded])[str(loaded)]!=lib_before[loaded.relative_to(root).as_posix()]:
        raise RuntimeError('Loaded REBOUND binary missing from provenance')
    paths = [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    paths += ['scripts/fixed_j2_ias.py','scripts/assess_fixed_j2_ias.py','scripts/eih_year.py',
        'scripts/ias15_eih.py','scripts/ias15_reference.py','scripts/newton_year.py',
        'scripts/assess_sandbox_planets.py','docs/fixed-j2-ias-protocol.md']
    source_before = hashes(paths)
    report = dict(protocol='184',source_sha256=source_before,library_sha256=lib_before,
        native_sha256=native_before,environment=dict(numpy=np.__version__,scipy=scipy.__version__,
        rebound=library.__version__),cases={},complete=False,general_release=False)
    arrays = {}
    def save():
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        report['npz_sha256'] = hashes([output.with_suffix('.npz').resolve()]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for case in ('newton_one','newton_two','eih_two'):
            seed,times,period = model(case);m = np.array([b.mass for b in seed.bodies])
            initial = states(seed.bodies);fig = entries(seed);scale = scales(initial,m,fig,seed.settings.physics)
            row = dict(settings=asdict(seed.settings),masses_kg=m.tolist(),names=[b.name for b in seed.bodies],
                samples=len(times),duration_seconds=float(times[-1]),nominal_period_seconds=period,
                reference_levels=[],candidates={},reference_comparisons={})
            report['cases'][case] = row
            arrays[case+'_initial'],arrays[case+'_times'] = initial,times
            for i,(rtol,division) in enumerate(((1e-13,200),(3e-14,400),(3e-14,800))):
                start = perf_counter()
                values,budget,metadata = reference(seed,times,rtol,period/division)
                metadata['seconds'] = perf_counter()-start
                metadata['balance'] = balances(values,budget,seed)
                arrays[case+'_reference_'+str(i)] = values
                arrays[case+'_budgets_'+str(i)] = budget
                row['reference_levels'].append(metadata)
                save();print(case,'reference',i,metadata,flush=True)
            for i in (1,2):
                delta = (arrays[case+'_budgets_'+str(i)]-arrays[case+'_budgets_'+str(i-1)])/scale
                row['reference_comparisons'][str(i-1)+'_to_'+str(i)] = dict(
                    state=errors(arrays[case+'_reference_'+str(i-1)],arrays[case+'_reference_'+str(i)]),
                    maximum_scaled_budget_component=float(abs(delta).max()))
            last = row['reference_comparisons']['1_to_2']
            ref_ok = within(last['state'],.01,1e-5) and last['maximum_scaled_budget_component']<1e-10
            row['reference_passed'] = ref_ok
            expected = arrays[case+'_reference_2'];budgets = arrays[case+'_budgets_2']
            field = figure_force(initial[:,:3],m,fig)
            forces = m[:,None]*field
            wrong = forces.copy();wrong[0] = 0.
            row['reaction_negative_control'] = dict(correct_scaled_net_force=float(np.linalg.norm(forces.sum(axis=0))/np.linalg.norm(forces,axis=1).sum()),
                missing_reaction_scaled_net_force=float(np.linalg.norm(wrong.sum(axis=0))/np.linalg.norm(forces,axis=1).sum())) if case=='newton_one' else None
            functions = {'dop853':lambda:dop_trajectory(seed,times),
                'ias15_1e-9':lambda:ias_trajectory(seed,times,library,1e-9),
                'ias15_1e-11':lambda:ias_trajectory(seed,times,library,1e-11)}
            bounds = None
            for name,function in functions.items():
                values,stats = function();repeat,_ = function()
                np.testing.assert_array_equal(values[0],initial)
                np.testing.assert_array_equal(values,repeat)
                if bounds is None:bounds = stats['packet_endpoints']
                if bounds!=stats['packet_endpoints']:raise RuntimeError('Different packet endpoints')
                arrays[case+'_'+name] = values
                error = errors(values,expected);balance = balances(values,budgets,seed)
                passed = bool(ref_ok and within(error,.1,1e-4) and max(balance['corrected'].values())<1e-9)
                if case=='newton_one':passed = passed and balance['single_axis_angular_projection']<1e-9
                # Wrong conservation criteria are retained as negative diagnostics.
                point_values = []
                for q in values:
                    from scripts.fixed_j2_ias import quantities
                    point_values.append(quantities(q,m,(),seed.settings.physics)[0])
                point_energy_change = float(abs(np.array(point_values)-point_values[0]).max()/scale[0])
                if case.startswith('newton'):
                    passed = passed and point_energy_change>1e-6 and balance['raw']['angular']>1e-6
                if case=='newton_one':passed = passed and row['reaction_negative_control']['missing_reaction_scaled_net_force']>1e-3
                row['candidates'][name] = dict(error=error,
                    per_body={b.name:errors(values[:,i],expected[:,i]) for i,b in enumerate(seed.bodies)},
                    balance=balance,point_energy_without_V2_scaled_change=point_energy_change,
                    statistics=stats,repeat_bitexact=True,checks_passed=bool(passed))
                print(case,name,error,balance,'passed',passed,flush=True)
            row['packet_endpoints_equal'] = True;row['packets'] = len(bounds)
            durations = {name:[] for name in functions}
            for iteration in range(3):
                for name in (list(functions) if iteration%2==0 else list(reversed(functions))):
                    start = perf_counter();values,_ = functions[name]();elapsed = perf_counter()-start
                    np.testing.assert_array_equal(values,arrays[case+'_'+name]);durations[name].append(elapsed)
            row['cost'] = {name:dict(seconds=v,median_seconds=median(v)) for name,v in durations.items()}
            save()
        report['warnings'] = [str(w.message) for w in caught]
    if hashes(paths)!=source_before or hashes(native_paths)!=native_before or library_hashes(library)!=lib_before:
        raise RuntimeError('Source or actual binary changed during calculation')
    report['source_library_native_unchanged'] = True
    report['complete'] = True
    report['checks_passed'] = all(c['checks_passed'] for row in report['cases'].values() for c in row['candidates'].values())
    save();print('complete',output,'checks_passed',report['checks_passed'],flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True);parser.add_argument('--library-directory',type=Path,required=True)
    args = parser.parse_args();run(args.output,args.library_directory)


if __name__=='__main__':main()
