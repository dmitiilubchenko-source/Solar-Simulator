"""Connect separate Decimal identities to existing matrix/native source paths."""
import argparse
from decimal import localcontext
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.noether_identities import convert,forces,response,pack,dec
from scripts.assess_noether_identities import verified_pilot
from scripts.fixed_j2_ias import entries,sources
from scripts.fixed_j2_year import inputs
from scripts.eih_year import force_terms
from scripts.newton_year import ROOT,hashes
from solar_simulator.native_forces import prepare as native_prepare
from solar_simulator.oblateness import prepare,acceleration
from solar_simulator.relativity import C
from solar_simulator.simulation import G

BLOCKS=(('energy',slice(0,1)),('momentum',slice(1,4)),('angular',slice(4,7)))


def source_metrics(actual,expected):
    actual,expected=np.asarray(actual),np.asarray(expected)
    if actual.shape!=(3,7) or expected.shape!=actual.shape or not np.isfinite(actual).all() or not np.isfinite(expected).all():
        raise ValueError('Invalid source bridge arrays')
    groups={}
    for i,name in enumerate(('figure_torque','pn2','pn_q2')):
        groups[name]={}
        for block,s in BLOCKS:
            signal=float(np.linalg.norm(expected[i,s]));error=float(np.linalg.norm(actual[i,s]-expected[i,s]))
            relative=error/signal if signal else (0. if error==0. else None)
            groups[name][block]=dict(signal_SI=signal,error_SI=error,relative_error=relative,
                active=bool(signal),checks_passed=bool(relative is not None and relative<5e-10))
    return dict(groups=groups,checks_passed=all(r['checks_passed'] for g in groups.values() for r in g.values()))


def bridge(state,masses,figures,prepared_figures):
    q=np.asarray(state,dtype=float);m=np.asarray(masses,dtype=float);p,v=q[:,:3],q[:,3:]
    with localcontext() as context:
        context.prec=90
        pd,vd,md,fd=convert(q,m,figures);g,c=dec(G),dec(C)
        an,ap,aq=forces(pd,vd,md,fd,g,c)
        _,strong,_=forces(pd,vd,md,[],g,c/10)
        r2=response(pd,vd,md,ap,g,c);rq=response(pd,vd,md,aq,g,c)
        torque=pack(pd,vd,[[mass*x for x in row] for mass,row in zip(md,aq)])[4:]
        expected=[[dec(0)]*4+torque,pack(pd,vd,r2),pack(pd,vd,rq)]
        expected_text=[[str(x) for x in row] for row in expected]
    def array(a):return np.array([[float(x) for x in row] for row in a])
    an,ap,aq,strong=map(array,(an,ap,aq,strong))
    matrix_n,matrix_pn=force_terms(p,v,G*m,C)
    native_q=acceleration(p,m,prepared_figures)
    native=native_prepare(m)
    def gap(a,b):return float(np.linalg.norm(a-b,axis=1).max()/np.linalg.norm(b,axis=1).max())
    row=dict(newton_relative_error=gap(matrix_n,an),matrix_pn_relative_error=gap(matrix_pn,ap),
        figure_relative_error=gap(native_q,aq),native_full_relative_error=gap(native(p,v,C),an+ap),
        native_amplified_pn_relative_error=gap(native(p,v,C/10)-native(p,v),strong),
        sources=source_metrics(sources(p,v,m,matrix_pn,native_q),array(expected)),
        decimal_source_components_SI=expected_text)
    row['checks_passed']=bool(all(row[k]<5e-13 for k in ('newton_relative_error','matrix_pn_relative_error','figure_relative_error'))
        and row['native_full_relative_error']<3e-14 and row['native_amplified_pn_relative_error']<3e-9
        and row['sources']['checks_passed'])
    return row


def run(output,pilot_receipt,identity_receipt):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or output.with_suffix('.json').exists():
        raise ValueError('Use fresh project .tools output')
    pilot_receipt=Path(pilot_receipt).resolve();identity_receipt=Path(identity_receipt).resolve()
    pilot=verified_pilot(pilot_receipt);audit=json.loads(identity_receipt.read_bytes())
    if not audit['complete'] or not audit['checks_passed'] or not audit['source_input_dependencies_unchanged']:
        raise ValueError('Require complete qualified identity audit')
    for group in ('source_sha256','input_sha256'):
        if hashes(audit[group])!=audit[group]:raise ValueError('Identity source/input changed')
    if audit['input_sha256'].get(str(pilot_receipt))!=hashes([pilot_receipt])[str(pilot_receipt)]:
        raise ValueError('Identity audit refers to a different pilot')
    seed,*_=inputs();fig=entries(seed);working=prepare(seed.bodies,seed.settings.figures)
    sources_bound=hashes(['docs/noether-identities-protocol.md','scripts/bridge_noether_sources.py','tests/test_noether_source_bridge.py'])
    bindings=hashes([pilot_receipt,pilot_receipt.with_suffix('.npz'),identity_receipt])
    report=dict(complete=False,checks_passed=False,source_sha256=sources_bound,input_sha256=bindings,cases={},
        original_global_visibility_requalified=False,annual_source_balances_verified=False,
        trajectories_reintegrated=False,runtime_modified=False,general_release=False)
    output.parent.mkdir(parents=True,exist_ok=True)

    def save():output.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')

    save();start=perf_counter()
    try:
        with np.load(pilot_receipt.with_suffix('.npz'),allow_pickle=False) as data:
            for name in audit['cases']:
                rows=[];report['cases'][name]=rows
                for i,q in enumerate(data[name]):
                    row=bridge(q,pilot['masses_kg'],fig,working)
                    row.update(index=i,time_seconds=float(data['times'][i]));rows.append(row);save()
                print(name,'source bridge',all(r['checks_passed'] for r in rows),flush=True)
        verified_pilot(pilot_receipt)
        if any(hashes(g)!=g for g in (sources_bound,bindings,audit['source_sha256'],audit['input_sha256'])):
            raise ValueError('Source bridge provenance changed')
        report.update(complete=True,checks_passed=all(r['checks_passed'] for rows in report['cases'].values() for r in rows),
            source_input_dependencies_unchanged=True,samples=30,wall_seconds=perf_counter()-start)
        save()
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error));save();raise
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('output','pilot-receipt','identity-receipt'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if not run(args.output,args.pilot_receipt,args.identity_receipt)['checks_passed']:
        raise RuntimeError('Noether source bridge failed; evidence retained')


if __name__=='__main__':main()
