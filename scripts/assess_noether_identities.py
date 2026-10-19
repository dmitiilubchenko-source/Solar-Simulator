"""Audit all frozen ten-body snapshots without advancing any trajectory."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.noether_identities import snapshot,precision_agreement
from scripts.assess_solar_noether import epoch_grid
from scripts.fixed_j2_ias import entries
from scripts.fixed_j2_year import inputs
from scripts.newton_year import ROOT,hashes

PROTOCOL='docs/noether-identities-protocol.md'


def verified_pilot(path):
    path=Path(path).resolve();doc=json.loads(path.read_bytes())
    if not doc['complete'] or not doc['numerical_checks_passed'] or not doc['source_input_dependencies_unchanged']:
        raise ValueError('Require complete numerical pilot')
    for key in ('source_sha256','input_sha256','dependency_sha256'):
        if hashes(doc[key])!=doc[key]:raise ValueError('Changed pilot source/input/dependency')
    if hashes([path.with_suffix('.npz')]).popitem()[1]!=doc['npz_sha256']:
        raise ValueError('Changed pilot snapshot archive')
    np.testing.assert_array_equal(doc['epochs_seconds'],epoch_grid())
    return doc


def controls_passed(rows):
    controls=[r['high']['levels'][-1]['negative_controls'] for r in rows]
    return bool(controls and max(r['missing_reaction_defect'] for r in controls)>1e-3
        and max(r['missing_static_energy_defect'] for r in controls)>1e-3
        and max(r['pair_only_pn_defect'] for r in controls)>1e-6
        and all(x is None or x>.9 for r in controls for b in r['omitted_sources'].values() for x in b.values()))


def run(output,pilot_receipt):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or output.with_suffix('.json').exists():
        raise ValueError('Use fresh project .tools output')
    pilot_receipt=Path(pilot_receipt).resolve();pilot=verified_pilot(pilot_receipt)
    seed,*_=inputs()
    if pilot['origin']!=asdict(seed.origin) or pilot['masses_kg']!=[b.mass for b in seed.bodies]:
        raise ValueError('Nominal calendar/masses mismatch')
    sources=hashes([PROTOCOL,'scripts/noether_identities.py','scripts/assess_noether_identities.py',
        'tests/test_noether_identities.py','tests/test_noether_identity_audit.py'])
    bindings=hashes([pilot_receipt,pilot_receipt.with_suffix('.npz')])
    report=dict(protocol=PROTOCOL,complete=False,checks_passed=False,source_sha256=sources,input_sha256=bindings,
        cases={},original_global_visibility_passed=pilot['full_source_observability_passed'],
        original_global_visibility_requalified=False,trajectories_reintegrated=False,runtime_modified=False,
        annual_source_balances_verified=False,jpl_comparison=False,general_release=False)
    output.parent.mkdir(parents=True,exist_ok=True)

    def save():output.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')

    save();start=perf_counter()
    try:
        with np.load(pilot_receipt.with_suffix('.npz'),allow_pickle=False) as data:
            np.testing.assert_array_equal(data['times'],epoch_grid())
            names=[*('reference_'+str(i) for i in range(3)),*pilot['candidates']]
            for name in names:
                values=data[name]
                if values.shape!=(5,10,6) or not np.isfinite(values).all():raise ValueError('Invalid frozen snapshots')
                rows=[];report['cases'][name]=dict(snapshots=rows,checks_passed=False)
                for index,q in enumerate(values):
                    now=perf_counter()
                    low=snapshot(q,pilot['masses_kg'],entries(seed),70)
                    high=snapshot(q,pilot['masses_kg'],entries(seed),90)
                    agreement=precision_agreement(low,high)
                    row=dict(index=index,time_seconds=float(data['times'][index]),low=low,high=high,
                        precision_agreement=agreement,wall_seconds=perf_counter()-now,
                        checks_passed=bool(low['checks_passed'] and high['checks_passed'] and agreement['checks_passed']))
                    rows.append(row);save()
                    print(name,index,'identities',row['checks_passed'],flush=True)
                report['cases'][name].update(negative_controls_passed=controls_passed(rows),
                    checks_passed=bool(all(r['checks_passed'] for r in rows) and controls_passed(rows)))
                save()
        verified_pilot(pilot_receipt)
        if hashes(sources)!=sources or hashes(bindings)!=bindings:raise ValueError('Identity source/input changed')
        report.update(complete=True,checks_passed=all(c['checks_passed'] for c in report['cases'].values()),
            source_input_dependencies_unchanged=True,wall_seconds=perf_counter()-start,samples=30)
        save()
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error));save();raise
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--pilot-receipt',type=Path,required=True)
    args=parser.parse_args()
    if not run(args.output,args.pilot_receipt)['checks_passed']:
        raise RuntimeError('Identity audit failed; evidence retained')


if __name__=='__main__':main()
