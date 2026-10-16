"""Active step-cap refinement of the unchanged edited-J2 candidate cache."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter
import warnings

import numpy as np

from scripts.edited_j2 import CASES,fixture,verify_branch,reference_gate,metrics,agreement
from scripts.fixed_j2_ias import reference,balances
from scripts.kepler_cache import load_receipt
from scripts.newton_year import ROOT,hashes
from scripts.assess_sandbox_planets import states


def run(input_path,output):
    input_path=Path(input_path).resolve();output=Path(output).resolve()
    if output.with_suffix('.json').exists() or output.with_suffix('.npz').exists():
        raise ValueError('Use a fresh output path')
    prior,raw=load_receipt(input_path,ROOT)
    if (not prior['complete'] or not prior['checks_passed'] or tuple(prior['cases'])!=CASES
            or not prior['source_input_native_scipy_unchanged']):
        raise ValueError('Expected the completed six-case audit194')
    for group in ('input_sha256','native_sha256','scipy_source_sha256'):
        if hashes(prior[group])!=prior[group]:raise ValueError('Prior binding changed: '+group)
    sources=dict(prior['source_sha256'])
    sources.update(hashes(['scripts/refine_edited_j2.py','scripts/kepler_cache.py',
        'docs/edited-j2-refinement-protocol.md']))
    inputs=hashes([input_path,input_path.with_suffix('.npz')])
    output.parent.mkdir(parents=True,exist_ok=True)
    report=dict(protocol='docs/edited-j2-refinement-protocol.md',source_sha256=sources,
        input_sha256=inputs,native_sha256=prior['native_sha256'],scipy_source_sha256=prior['scipy_source_sha256'],
        candidates_reintegrated=False,cases={},complete=False,general_release=False,runtime_modified=False)
    arrays={}
    def save():
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        report['npz_sha256']=hashes([output.with_suffix('.npz')]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    save()
    try:
        with warnings.catch_warnings(record=True) as caught,np.load(input_path.with_suffix('.npz'),allow_pickle=False) as cache:
            warnings.simplefilter('always')
            for case in CASES:
                parent,branch,times,period=fixture(case);seed=branch.child;old=prior['cases'][case]
                initial=states(seed.bodies);names=[b.name for b in seed.bodies]
                if (verify_branch(parent,branch)!=old['provenance']
                        or json.loads(json.dumps(asdict(seed.settings)))!=old['settings']
                        or names!=old['names'] or [b.mass for b in seed.bodies]!=old['masses_kg']):
                    raise ValueError('Prior model/IC/mass/provenance mismatch')
                np.testing.assert_array_equal(times,cache[case+'_times'])
                np.testing.assert_array_equal(initial,cache[case+'_initial'])
                row=dict(reference_levels=[],comparisons={},candidates={})
                report['cases'][case]=row;arrays[case+'_initial']=initial;arrays[case+'_times']=times
                for division in (1600,3200):
                    start=perf_counter();values,budget,metadata=reference(seed,times,3e-14,period/division)
                    metadata['wall_seconds']=perf_counter()-start
                    metadata['initial_roundtrip']=agreement(values[:1],initial[None],names)
                    metadata['balance']=balances(values,budget,seed)
                    arrays[case+'_reference_'+str(division)]=values;arrays[case+'_budgets_'+str(division)]=budget
                    row['reference_levels'].append(metadata);save()
                    print(case,'reference',division,'RHS',metadata['rhs_calls'],'seconds',metadata['wall_seconds'],flush=True)
                previous=arrays[case+'_reference_1600'];expected=arrays[case+'_reference_3200']
                pb=arrays[case+'_budgets_1600'];budgets=arrays[case+'_budgets_3200']
                row['comparisons']['old2_to_1600']=reference_gate(cache[case+'_reference_2'],previous,
                    cache[case+'_budgets_2'],pb,seed)
                last=reference_gate(previous,expected,pb,budgets,seed)
                row['comparisons']['1600_to_3200']=last
                row['rhs_increased']=(old['reference_levels'][-1]['rhs_calls']<row['reference_levels'][0]['rhs_calls']
                    <row['reference_levels'][1]['rhs_calls'])
                row['reference_passed']=bool(last['checks_passed'] and row['rhs_increased'])
                for name,old_candidate in old['candidates'].items():
                    values=cache[case+'_'+name]
                    np.testing.assert_array_equal(values[0],initial)
                    candidate=metrics(values,expected,budgets,seed,row['reference_passed'])
                    candidate['prior_checks_passed']=old_candidate['checks_passed']
                    candidate['checks_passed']=bool(candidate['checks_passed']
                        and candidate['balance']['raw']['angular']>1e-6)
                    row['candidates'][name]=candidate
                    print(case,name,'relative',candidate['relative_pair'],'corrected',candidate['balance']['corrected'],
                        'passed',candidate['checks_passed'],flush=True)
                save()
            report['warnings']=[str(w.message) for w in caught]
        for bindings in (sources,inputs,prior['native_sha256'],prior['scipy_source_sha256']):
            if hashes(bindings)!=bindings:raise ValueError('Scientific cache/source binding changed')
        report.update(complete=True,source_input_native_scipy_unchanged=True,
            checks_passed=all(c['checks_passed'] for row in report['cases'].values() for c in row['candidates'].values()))
        save()
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error));save();raise
    print('complete',output,'checks_passed',report['checks_passed'],flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not run(args.input,args.output)['checks_passed']:raise RuntimeError('Refinement checks failed; result preserved')


if __name__=='__main__':main()
