"""Independent IAS15/Decimal comparison and paired cost, outside runtime."""
import argparse
from dataclasses import replace
from decimal import Decimal as D,localcontext
import hashlib
import json
from pathlib import Path
import statistics
from time import perf_counter
import warnings

import numpy as np

from scripts.assess_continuous import invariant_rows
from scripts.assess_kepler_holdout import CASES,holdout_fixture
from scripts.assess_kepler_phase import ROOT,decimal_relative,differences,maximum,fingerprints
from scripts.ias15_reference import load_library,library_hashes,ias_trajectory,dop_trajectory,EPSILONS,VERSION
from scripts.kepler_cache import load_receipt
from solar_simulator.simulation import G
from solar_simulator.vector3 import Vector3


def metrics(seed,times,values,expected):
    initial_e,initial_p,initial_l=invariant_rows(seed.bodies)
    momentum_scale=sum(b.mass*b.velocity.magnitude() for b in seed.bodies)
    energy_drift=angular_drift=linear_drift=orbital_drift=0.
    rows=[]
    with localcontext() as context:
        context.prec=110
        mu=D.from_float(G)*sum(
            D.from_float(float(b.mass)) for b in seed.bodies)
        def orbital_energy(relative):
            return sum(x*x for x in relative[3:])/2-mu/sum(x*x for x in relative[:3]).sqrt()
        orbital_initial=orbital_energy(decimal_relative(values[0]))
        for state,reference in zip(values,expected):
            relative=decimal_relative(state)
            rows.append(differences((relative[:3],relative[3:]),reference))
            orbital_drift=max(orbital_drift,float(abs((orbital_energy(relative)-orbital_initial)/orbital_initial)))
            bodies=[replace(body,position=Vector3(*map(float,row[:3])),
                            velocity=Vector3(*map(float,row[3:]))) for body,row in zip(seed.bodies,state)]
            energy,linear,angular=invariant_rows(bodies)
            energy_drift=max(energy_drift,abs((energy-initial_e)/initial_e))
            angular_drift=max(angular_drift,float(np.linalg.norm(angular-initial_l)/np.linalg.norm(initial_l)))
            linear_drift=max(linear_drift,float(np.linalg.norm(linear-initial_p)/momentum_scale))
    maximum_errors=maximum(rows)
    passed=(maximum_errors['position_metres']<.1 and maximum_errors['velocity_m_per_s']<1e-6
            and max(energy_drift,angular_drift,linear_drift)<1e-10)
    return dict(**maximum_errors,relative_energy_drift=energy_drift,
        relative_angular_drift=angular_drift,scaled_momentum_drift=linear_drift,
        specific_orbital_energy_drift=orbital_drift,checks_passed=passed,
        worst_position_time_seconds=float(times[max(range(len(rows)),key=lambda i:rows[i]['position_metres'])]),
        sampled_errors=rows)


def source_hashes():
    sources=fingerprints()
    for name in ('scripts/ias15_reference.py','scripts/assess_ias15.py',
                 'scripts/assess_kepler_holdout.py','scripts/kepler_roundoff.py',
                 'docs/ias15-comparison-protocol.md','requirements/research-ias15.txt'):
        sources[name]=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
    return sources


def run(reference_path,output,library):
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous results')
    reference,reference_raw=load_receipt(reference_path,ROOT)
    with np.load(reference_path.with_suffix('.npz'),allow_pickle=False) as cache:
        cached={key:cache[key].copy() for key in cache.files}
    source=source_hashes();external=library_hashes(library)
    results={};arrays={};captured=[]
    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter('always')
        for name,e,anomaly,permuted in CASES:
            seed,times=holdout_fixture(e,anomaly,permuted)
            np.testing.assert_array_equal(times,cached[f'{name}_times'])
            expected=[tuple(tuple(map(D,group)) for group in row)
                      for row in reference['results'][name]['decimal_reference']]
            methods={'dop853':lambda:dop_trajectory(seed,times)}
            methods.update({f'ias15_{epsilon}':lambda epsilon=epsilon:ias_trajectory(seed,times,library,epsilon)
                            for epsilon in EPSILONS})
            values={};rows={};stats={}
            for mode,operation in methods.items():
                value,counts=operation()
                np.testing.assert_array_equal(value[0],cached[f'{name}_original'][0])
                if mode=='dop853':
                    np.testing.assert_array_equal(value,cached[f'{name}_original'])
                else:
                    repeat,_=operation();np.testing.assert_array_equal(value,repeat)
                    counted,counters=ias_trajectory(seed,times,library,counts['epsilon'],count_forces=True)
                    np.testing.assert_array_equal(value,counted)
                    counts['force_evaluations']=counters['force_evaluations']
                    counts['counter_run_separate']=True
                values[mode]=value;stats[mode]=counts
                rows[mode]=dict(**metrics(seed,times,value,expected),**counts)
                arrays[f'{name}_{mode}']=value
                print(name,mode,{k:v for k,v in rows[mode].items() if k not in ('sampled_errors','packet_endpoints')},flush=True)
            assert len(stats['dop853']['packet_endpoints'])==131
            assert all(row['packet_endpoints']==stats['dop853']['packet_endpoints'] for row in stats.values())
            cost={key:[] for key in methods}
            # The first evaluation above warmed each method, plus one explicit
            # warmup immediately before three timed alternating runs.
            for key,operation in methods.items():
                value,_=operation();np.testing.assert_array_equal(value,values[key])
            for iteration in range(3):
                order=list(methods) if iteration%2==0 else list(reversed(methods))
                for key in order:
                    start=perf_counter();value,_=methods[key]();elapsed=perf_counter()-start
                    np.testing.assert_array_equal(value,values[key])
                    cost[key].append(elapsed)
            arrays[f'{name}_times']=times
            results[name]=dict(samples=len(times),initial_state=values['dop853'][0].tolist(),
                oracle_uncertainty=reference['results'][name]['oracle_uncertainty'],
                methods=rows,cost={key:dict(raw_seconds=data,median_seconds=statistics.median(data))
                                  for key,data in cost.items()})
    assert source==source_hashes() and external==library_hashes(library)
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest()==hashlib.sha256(reference_raw).hexdigest()
    np.savez_compressed(output.with_suffix('.npz'),**arrays)
    methods=['dop853']+[f'ias15_{epsilon}' for epsilon in EPSILONS]
    checks={mode:all(row['methods'][mode]['checks_passed'] for row in results.values()) for mode in methods}
    receipt=dict(protocol='docs/ias15-comparison-protocol.md',source_sha256=source,
        reference_sha256=hashlib.sha256(reference_raw).hexdigest(),
        npz_sha256=hashlib.sha256(output.with_suffix('.npz').read_bytes()).hexdigest(),
        rebound_version=VERSION,library_files_sha256=external,source_unchanged=True,
        reference_unchanged=True,library_unchanged=True,dop_control_bitexact=True,
        repeats_and_counters_bitexact=True,identical_packet_boundaries=True,
        results=results,per_method_checks_passed=checks,
        checks_passed=all(checks[f'ias15_{epsilon}'] for epsilon in EPSILONS),
        warnings=[str(item.message) for item in captured],
        runtime_modified=False,general_release_passed=False,
        timing_compares_full_implementations_not_integrator_formula_only=True)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(receipt,stream,indent=2,allow_nan=False);stream.write('\n')
    print('Saved',output,'checks_passed',receipt['checks_passed'],flush=True)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--library',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();output=args.output.resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    library=load_library(args.library)
    receipt=run(args.reference.resolve(),output,library)
    if not receipt['checks_passed']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
