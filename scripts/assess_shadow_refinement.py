"""Nested fixed-grid convergence; reuses338 high-precision oracle samples."""
import argparse
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.assess_kepler_phase import ROOT,differences,maximum
from scripts.assess_rust_adaptive import provenance
from scripts.assess_rust_trace import sha
from scripts.assess_kepler_shadow import diagnostic_gate
from scripts.kepler_shadow import rk_step,relative_rhs,trace_grid,exact_elapsed,invariant_drifts

PROTOCOL='docs/rust-adaptive-refinement-protocol.md'
CACHE='docs/rust-adaptive-shadow-validation.json'


def substep(h,divisor):
    if divisor not in (2,4) or not np.isfinite(h) or h<=0:
        raise ValueError('Use predeclared positive dyadic subdivision2/4')
    with localcontext() as context:
        context.prec=110
        value=D.from_float(h)/divisor
        if F(value)*divisor!=F(h):raise ArithmeticError('Inexact dyadic substep')
        return value


def refined_trajectory(initial,steps,times,header,mu,precision,divisor):
    if precision not in (50,80) or divisor not in (2,4):raise ValueError('Invalid refinement')
    wanted=set(map(float,times[1:]));values=[tuple(initial)];elapsed=[D(0)]
    state=tuple(initial);clock=F(0);previous=0.
    with localcontext() as context:
        context.prec=precision
        a=tuple(tuple(D.from_float(x) for x in row) for row in header['a'])
        b=tuple(D.from_float(x) for x in header['b'])
        for next_time,h in steps:
            if not previous<next_time or h!=next_time-previous:raise ValueError('Changed macro grid')
            delta=substep(h,divisor)
            for _ in range(divisor):state=rk_step(state,delta,a,b,lambda y:relative_rhs(y,mu))
            previous=next_time;clock+=F(h)
            if next_time in wanted:values.append(state);elapsed.append(exact_elapsed(clock))
    if len(values)!=len(times) or previous!=times[-1]:raise ValueError('Missing refinement epoch')
    return values,elapsed


def run(output,cache_path=ROOT/CACHE):
    output=Path(output).resolve()
    if output.exists() or output.with_suffix('.npz').exists():raise FileExistsError('Preserve prior refinement')
    if not output.is_relative_to((ROOT/'.tools').resolve()):raise ValueError('Use fresh .tools output')
    cache_path=Path(cache_path).resolve()
    cache=json.loads(cache_path.read_text(encoding='utf-8'))
    if not cache['complete'] or len(cache['results'])!=9:raise ValueError('Require complete338 cache')
    source={**cache['source_sha256'],PROTOCOL:sha(ROOT/PROTOCOL),
        'scripts/assess_shadow_refinement.py':sha(ROOT/'scripts/assess_shadow_refinement.py')}
    archive=(ROOT/cache['sample_archive']) if 'sample_archive' in cache else cache_path.with_suffix('.npz')
    inputs={**cache['input_sha256'],str(cache_path):sha(cache_path),str(archive):cache['npz_sha256']}
    for name,value in source.items():
        if sha(ROOT/name)!=value:raise ValueError('Changed338 source: '+name)
    for name,value in inputs.items():
        if sha(ROOT/name)!=value:raise ValueError('Changed338 input: '+name)
    with np.load(archive,allow_pickle=False) as data:
        frozen={k:data[k].copy() for k in data.files}
    # A new338 run can point to a regenerated337 receipt in a fresh local path.
    # Resolve that exact, SHA-bound receipt, rather than the original public paths.
    trace_receipts=[]
    for name in cache['input_sha256']:
        if Path(name).suffix=='.json':
            candidate=json.loads((ROOT/name).read_text(encoding='utf-8'))
            if candidate.get('protocol')=='docs/rust-adaptive-trace-protocol.md':
                trace_receipts.append(candidate)
    if len(trace_receipts)!=1:raise ValueError('Expected one bound337 receipt')
    trace=trace_receipts[0]
    original=json.loads((ROOT/'docs/rust-adaptive-prototype-validation.json').read_text())
    snapshot=provenance(output.parent/(output.stem+'-sources'))
    report=dict(protocol=PROTOCOL,complete=False,production_eligible=False,runtime_modified=False,
        source_sha256=source,input_sha256=inputs,provenance=snapshot,results={})
    arrays={};start=perf_counter()
    def save():output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save()
    try:
        for name,coarse in cache['results'].items():
            row=original['results'][name]
            header,initial,steps=trace_grid(ROOT/trace['results'][name]['trace_path'],
                row['baseline_statistics']['packet_endpoints'],row['rust_statistics'])
            times=frozen[name+'_times'];mu=D(coarse['mu_exact'])
            decode=lambda key:[tuple(map(D,y)) for y in frozen[name+'_'+key]]
            expected={key:decode(key+'_oracle100') for key in ('prepared','actual')}
            coarse_values=decode('shadow80')
            pair=lambda y:(y[:3],y[3:])
            # Bind cached high-precision arrays to the published338 error metrics.
            for key in expected:
                errors=maximum([differences(pair(y),pair(r)) for y,r in zip(coarse_values,expected[key])])
                if errors!=coarse[key+'_error']:raise ValueError('Cached338 metric mismatch: '+name)
            variants={}
            for divisor in (2,4):
                values={};stamp=perf_counter()
                for precision in (50,80):
                    values[precision],elapsed=refined_trajectory(initial,steps,times,header,mu,precision,divisor)
                    arrays[f'{name}_d{divisor}_p{precision}']=np.array([[str(x) for x in y] for y in values[precision]])
                if list(map(str,elapsed))!=frozen[name+'_elapsed'].tolist():raise ValueError('Changed exact elapsed')
                convergence=maximum([differences(pair(a),pair(b)) for a,b in zip(values[50],values[80])])
                if convergence['position_metres']>=1e-6 or convergence['velocity_m_per_s']>=1e-12:
                    raise ArithmeticError('Refined precision check failed')
                drift=invariant_drifts(values[80],mu)
                summary=dict(precision_difference=convergence,relative_invariants=drift,
                    macrosteps=len(steps),substeps=len(steps)*divisor,seconds=perf_counter()-stamp)
                for key in expected:
                    errors=[differences(pair(y),pair(r)) for y,r in zip(values[80],expected[key])]
                    summary[key+'_error']=maximum(errors);summary['sampled_'+key+'_errors']=errors
                    summary[key+'_diagnostic_gate']=diagnostic_gate(maximum(errors),drift)
                variants[str(divisor)]=summary
            ratios={quantity:[coarse['prepared_error'][quantity]/variants['2']['prepared_error'][quantity],
                variants['2']['prepared_error'][quantity]/variants['4']['prepared_error'][quantity]]
                for quantity in ('position_metres','velocity_m_per_s')}
            report['results'][name]=dict(coarse_prepared_error=coarse['prepared_error'],
                original_gate_passed=coarse['original_gate_passed'],variants=variants,
                prepared_error_ratios_full_to_half_and_half_to_quarter=ratios)
            arrays[name+'_times']=times;save()
            print(name,'d2',variants['2']['prepared_error'],'d4',variants['4']['prepared_error'],
                'ratios',ratios['position_metres'],flush=True)
        if any(sha(ROOT/n)!=h for n,h in {**source,**inputs}.items()):raise ValueError('Audit inputs changed')
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        report.update(complete=True,source_unchanged=True,input_unchanged=True,npz_sha256=sha(output.with_suffix('.npz')),
            all_refined_diagnostic_cases_passed=all(v[key+'_diagnostic_gate']
                for row in report['results'].values() for v in row['variants'].values() for key in ('prepared','actual')))
    except BaseException as error:report['failure']=dict(type=type(error).__name__,message=str(error));raise
    finally:report['wall_seconds']=perf_counter()-start;save()
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--cache',type=Path,default=ROOT/CACHE)
    args=parser.parse_args();result=run(args.output,args.cache)
    return 0 if result['all_refined_diagnostic_cases_passed'] else 2


if __name__=='__main__':raise SystemExit(main())
