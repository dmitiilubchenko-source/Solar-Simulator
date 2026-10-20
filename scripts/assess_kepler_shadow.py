"""Decimal50/80 fixed-grid diagnostic; no production solver changes."""
import argparse
from decimal import Decimal as D, localcontext
import json
from pathlib import Path
import platform
from time import perf_counter

import numpy as np

from scripts.assess_kepler_holdout import CASES, holdout_fixture, reference_rows
from scripts.assess_kepler_phase import ROOT, fixture, differences, maximum
from scripts.assess_rust_adaptive import provenance, sources
from scripts.assess_rust_trace import sha, bits
from scripts.assess_sandbox_planets import states
from scripts.kepler_reference import propagate
from scripts.kepler_shadow import trace_grid, trajectory, invariant_drifts
from solar_simulator.simulation import G

PROTOCOL='docs/rust-adaptive-shadow-protocol.md'
TRACE_RECEIPT='docs/rust-adaptive-trace-validation.json'
ORIGINAL='docs/rust-adaptive-prototype-validation.json'


def diagnostic_gate(error,drift):
    return (error['position_metres']<.1 and error['velocity_m_per_s']<1e-6
        and drift['relative_specific_energy_drift']<1e-10 and drift['relative_angular_drift']<1e-10)


def run(trace_receipt,output):
    output=Path(output).resolve();trace_receipt=Path(trace_receipt).resolve()
    if output.exists() or output.with_suffix('.npz').exists():
        raise FileExistsError('Preserve previous shadow result')
    if not output.is_relative_to((ROOT/'.tools').resolve()):
        raise ValueError('Use a new project .tools output')
    trace=json.loads(trace_receipt.read_text(encoding='utf-8'))
    original=json.loads((ROOT/ORIGINAL).read_text(encoding='utf-8'))
    if not trace['complete'] or not trace['all_modes_bitexact'] or trace['production_eligible']:
        raise ValueError('Expected complete337 transparent replay')
    for name,expected in trace['source_sha256'].items():
        if sha(ROOT/name)!=expected: raise ValueError('Changed337 source: '+name)
    inputs={str(trace_receipt):sha(trace_receipt),**trace['input_sha256']}
    for name,expected in trace['input_sha256'].items():
        if sha(ROOT/name)!=expected: raise ValueError('Changed337 input: '+name)
    with np.load(ROOT/original['sample_archive'],allow_pickle=False) as data:
        old={k:data[k].copy() for k in data.files}
    fingerprints=sources()
    for name in (PROTOCOL,'scripts/assess_kepler_shadow.py','scripts/kepler_shadow.py',
            'scripts/assess_rust_trace.py','scripts/assess_kepler_force_rounding.py'):
        fingerprints[name]=sha(ROOT/name)
    snapshot=provenance(output.parent/(output.stem+'-sources'))
    report=dict(protocol=PROTOCOL,complete=False,production_eligible=False,runtime_modified=False,
        source_sha256=fingerprints,input_sha256=inputs,provenance=snapshot,
        environment=dict(python=platform.python_version(),numpy=np.__version__),
        scope='Relative Newton equation, preparedIC, exact recorded h, binary64 A/B; Decimal50/80',
        results={})
    arrays={};start=perf_counter()
    def save():
        output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save()
    try:
        cases=[('holdout_'+name,*holdout_fixture(e,a,p)) for name,e,a,p in CASES]
        cases += [('original_'+str(e),*fixture(e)) for e in (0.,.5,.95)]
        names={n for n,_,_ in cases}
        if names!=set(trace['results']) or names!=set(original['results']):
            raise ValueError('All nine cases are required')
        grids={}
        for name,seed,times in cases:
            row=trace['results'][name];request=original['results'][name]['input_request']
            path=(ROOT/row['trace_path']).resolve()
            if not path.is_relative_to(ROOT.resolve()) or sha(path)!=row['trace_sha256']:
                raise ValueError('Changed337 trace: '+name)
            inputs[str(path)]=row['trace_sha256']
            grid=trace_grid(path,original['results'][name]['baseline_statistics']['packet_endpoints'],
                original['results'][name]['rust_statistics'])
            initial=states(seed.bodies)
            relative=initial[1]-initial[0]
            if (not np.array_equal(times,old[name+'_times']) or request['times']!=times.tolist()
                    or request['masses']!=[b.mass for b in seed.bodies]
                    or np.asarray(request['states'],dtype='>f8').tobytes()!=initial.astype('>f8').tobytes()
                    or b''.join(bits(float(x)) for x in grid[1])!=relative.astype('>f8').tobytes()):
                raise ValueError('Changed initial state or output grid: '+name)
            grids[name]=grid
        for name,seed,times in cases:
            header,initial,steps=grids[name]
            with localcontext() as context:
                context.prec=110
                mu=D.from_float(G)*sum(D.from_float(b.mass) for b in seed.bodies)
            values={};cost={}
            for precision in (50,80):
                stamp=perf_counter()
                values[precision],elapsed=trajectory(initial,steps,times,header,mu,precision)
                cost['shadow'+str(precision)+'_seconds']=perf_counter()-stamp
                arrays[name+'_shadow'+str(precision)]=np.array([[str(x) for x in y] for y in values[precision]])
            paired=lambda y:(y[:3],y[3:])
            convergence=maximum([differences(paired(a),paired(b)) for a,b in zip(values[50],values[80])])
            if convergence['position_metres']>=1e-6 or convergence['velocity_m_per_s']>=1e-12:
                raise ArithmeticError('Decimal50/80 shadow failed to converge: '+name)
            expected,actual_uncertainty=reference_rows(seed,times)
            if np.asarray(expected,dtype='>f8').tobytes()!=old[name+'_reference'].astype('>f8').tobytes():
                raise ValueError('Existing actual-IC oracle differs from335: '+name)
            prepared=[];uncertainty=[];stamp=perf_counter()
            for elapsed_time in elapsed:
                low=propagate(initial[:3],initial[3:],mu,elapsed_time,precision=70)
                high=propagate(initial[:3],initial[3:],mu,elapsed_time,precision=100)
                uncertainty.append(differences(low,high));prepared.append(high)
            cost['prepared_oracle_seconds']=perf_counter()-stamp
            prepared_uncertainty=maximum(uncertainty)
            if (prepared_uncertainty['position_metres']>=1e-6
                    or prepared_uncertainty['velocity_m_per_s']>=1e-12
                    or prepared[0]!=paired(initial)):
                raise ArithmeticError('Prepared-IC oracle failed precision/t0 check')
            prepared_errors=[differences(paired(y),r) for y,r in zip(values[80],prepared)]
            actual_errors=[differences(paired(y),r) for y,r in zip(values[80],expected)]
            drift=invariant_drifts(values[80],mu)
            with localcontext() as context:
                context.prec=110
                clock_error=max(abs(t-D.from_float(float(epoch))) for t,epoch in zip(elapsed,times))
            report['results'][name]=dict(original_gate_passed=original['results'][name]['rust']['checks_passed'],
                original_error={k:original['results'][name]['rust'][k] for k in ('position_metres','velocity_m_per_s')},
                prepared_diagnostic_gate=diagnostic_gate(maximum(prepared_errors),drift),
                actual_diagnostic_gate=diagnostic_gate(maximum(actual_errors),drift),
                prepared_error=maximum(prepared_errors),actual_error=maximum(actual_errors),
                sampled_prepared_errors=prepared_errors,sampled_actual_errors=actual_errors,
                shadow50_80_difference=convergence,prepared_oracle_uncertainty=prepared_uncertainty,
                actual_oracle_uncertainty=actual_uncertainty,relative_invariants=drift,
                max_elapsed_minus_epoch_seconds=str(clock_error),accepted_steps=len(steps),
                mu_exact=str(mu),cost=cost)
            arrays[name+'_times']=times
            arrays[name+'_elapsed']=np.array(list(map(str,elapsed)))
            for mode,rows in (('prepared_oracle100',prepared),('actual_oracle100',expected)):
                arrays[name+'_'+mode]=np.array([[str(x) for group in row for x in group] for row in rows])
            save()
            print(name,'prepared',maximum(prepared_errors),'actual',maximum(actual_errors),
                'PASS' if report['results'][name]['prepared_diagnostic_gate'] else 'FAIL',flush=True)
        if (any(sha(ROOT/n)!=s for n,s in fingerprints.items())
                or any(sha(ROOT/n)!=s for n,s in inputs.items())):
            raise ValueError('Source or inputs changed during shadow audit')
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        report.update(complete=True,source_unchanged=True,input_unchanged=True,
            npz_sha256=sha(output.with_suffix('.npz')),
            all_prepared_diagnostic_cases_passed=all(v['prepared_diagnostic_gate'] for v in report['results'].values()),
            all_actual_diagnostic_cases_passed=all(v['actual_diagnostic_gate'] for v in report['results'].values()),
            original_passed_cases=sum(v['original_gate_passed'] for v in report['results'].values()))
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error));raise
    finally:
        report['wall_seconds']=perf_counter()-start;save()
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace-receipt',type=Path,default=ROOT/TRACE_RECEIPT)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=run(args.trace_receipt,args.output)
    return 0 if report['all_prepared_diagnostic_cases_passed'] and report['all_actual_diagnostic_cases_passed'] else 2


if __name__=='__main__':
    raise SystemExit(main())
