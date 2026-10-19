"""Measure readout arithmetic on frozen Noether snapshots; never reintegrate."""
import argparse
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.decimal_noether import compare_readouts
from scripts.fixed_j2_ias import entries, quantities, balances
from scripts.fixed_j2_year import inputs
from scripts.newton_year import ROOT, hashes
from scripts.assess_solar_noether import epoch_grid

PROTOCOL = 'docs/solar-noether-precision-protocol.md'


def run(output, pilot_receipt):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or any(output.with_suffix(s).exists() for s in ('.json','.npz')):
        raise ValueError('Use fresh project .tools output')
    pilot_receipt = Path(pilot_receipt).resolve()
    pilot = json.loads(pilot_receipt.read_bytes())
    if not pilot['complete'] or not pilot['source_input_dependencies_unchanged'] or not pilot['numerical_checks_passed']:
        raise ValueError('Require completed numerical pilot')
    for name in ('source_sha256','input_sha256','dependency_sha256'):
        if hashes(pilot[name]) != pilot[name]:
            raise ValueError('Changed pilot source/input/dependency')
    packet = pilot_receipt.with_suffix('.npz')
    if hashes([packet]).popitem()[1] != pilot['npz_sha256']:
        raise ValueError('Changed pilot trajectory/budget archive')
    seed,*_ = inputs()
    masses = np.array([b.mass for b in seed.bodies])
    fig,scale = entries(seed),np.array(pilot['scales_SI'])
    sources = hashes([PROTOCOL,'scripts/decimal_noether.py','scripts/assess_decimal_noether.py','tests/test_decimal_noether.py'])
    bindings = hashes([pilot_receipt,packet])
    result = dict(protocol=PROTOCOL,source_sha256=sources,input_sha256=bindings,
        complete=False,checks_passed=False,readouts={},trajectories_reintegrated=False,
        original_pilot_checks_passed=pilot['checks_passed'],original_pilot_visibility_passed=pilot['full_source_observability_passed'],
        original_failed_gate_requalified=False,runtime_modified=False,annual_balances_verified=False)
    arrays = {}
    output.parent.mkdir(parents=True,exist_ok=True)

    def save():
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        result['npz_sha256'] = hashes([output.with_suffix('.npz')]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')

    save()
    start = perf_counter()
    try:
        with np.load(packet,allow_pickle=False) as data:
            np.testing.assert_array_equal(data['times'],epoch_grid())
            keys = [*('reference_'+str(i) for i in range(3)),*pilot['candidates']]
            for name in keys:
                values = data[name]
                budget = data['budget_'+name.rsplit('_',1)[-1]] if name.startswith('reference_') else data['budget_2']
                rows = np.array([quantities(q,masses,fig,seed.settings.physics) for q in values])
                row,measured = compare_readouts(values,budget,masses,fig,scale,rows)
                row['float_balance'] = balances(values,budget,seed)
                result['readouts'][name] = row
                arrays.update({name+'_'+key:value for key,value in measured.items()})
                save()
                print(name,'precision passed',row['precision_checks_passed'],'decimal corrected',row['decimal_corrected'],flush=True)
        for group in (sources,bindings,*[pilot[n] for n in ('source_sha256','input_sha256','dependency_sha256')]):
            if hashes(group) != group:
                raise ValueError('Diagnostic source/input/actual dependency changed')
        result.update(complete=True,checks_passed=all(r['precision_checks_passed'] for r in result['readouts'].values()),
            wall_seconds=perf_counter()-start,source_input_dependencies_unchanged=True)
        save()
    except BaseException as error:
        result['failure'] = dict(type=type(error).__name__,message=str(error))
        save()
        raise
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pilot-receipt',type=Path,required=True)
    args = parser.parse_args()
    if not run(args.output,args.pilot_receipt)['checks_passed']:
        raise RuntimeError('Decimal readout convergence failed; evidence retained')


if __name__ == '__main__':
    main()
