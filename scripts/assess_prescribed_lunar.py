"""Controlled intervention R_Moon=DE441; no claim of a free spin forecast."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import perf_counter
import numpy as np
import scipy

from scripts import prescribed_lunar_control as control
from scripts import assess_free_lunar_year as annual
from scripts import free_lunar_diagnostics as diagnostic
from scripts import de441_reader as de
from scripts.assess_de441_reader import qualification as reader_qualified
from scripts.newton_year import ROOT, YEAR, hashes

PROTOCOL='docs/prescribed-lunar-protocol.md'
JOBS=('nominal','tight','reference_nominal','reference_tight')
TIMES=annual.TIMES


def free_receipt(path):
    row=json.loads(Path(path).read_bytes())
    if not row.get('checks_passed') or not annual.qualification(row):raise ValueError('Qualified free year required')
    for key in ('source_sha256','input_sha256'):
        if hashes(row[key]) != row[key]:raise ValueError('Free-year closure changed')
    annual.load_trajectories(Path(path).with_suffix(''),row)
    return row


def load_trajectories(directory, report):
    if set(report.get('jobs',{})) != set(JOBS):raise ValueError('All four control jobs required')
    values={}
    for name in JOBS:
        target=Path(directory)/(name+'.npz')
        if hashes([target]).popitem()[1] != report['jobs'][name]['npz_sha256']:raise ValueError('Control trajectory SHA changed')
        with np.load(target,allow_pickle=False) as packet:
            if set(packet.files) != {'times','states'}:raise ValueError('Exact control trajectory channels required')
            annual.validate_grid(packet['times']);values[name]=packet['states'].copy(order='K')
        if values[name].shape != (1462,81) or not np.isfinite(values[name]).all():raise ValueError('Complete finite controlled orbit required')
    return values


def vector_decomposition(free, controlled, expected, length):
    if (any(np.shape(v) != (1462,3) or not np.isfinite(v).all() for v in (free,controlled,expected))
            or not np.isfinite(length) or length<=0):raise ValueError('Finite complete relative vectors and positive unit required')
    df=free*length-expected;dc=controlled*length-expected;ds=(free-controlled)*length
    identity=df-dc-ds
    index=int(np.linalg.norm(df,axis=1).argmax())
    size=float(df[index]@df[index])
    return dict(free_pair_vector=df,control_pair_vector=dc,switch_vector=ds,identity_vector=identity),dict(
        identity_maximum_metres=float(np.linalg.norm(identity,axis=1).max()),
        switch_maximum_metres=float(np.linalg.norm(ds,axis=1).max()),
        worst_free_index=index,signed_switch_projection_at_worst_free=float(ds[index]@df[index]/size) if size else None)


def statistics(series, mask):
    shapes=dict(position_m=(1462,10),velocity_m_s=(1462,10),pair_vector_m=(1462,3))
    mask=np.asarray(mask)
    if mask.shape != (1462,) or mask.dtype != bool or not mask.any():raise ValueError('Nonempty annual mask required')
    if set(series)!=set(shapes) or any(np.shape(series[k])!=shape or not np.isfinite(series[k]).all() for k,shape in shapes.items()):
        raise ValueError('All finite body and pair channels required')
    p,v,pair=(series[k][mask] for k in shapes);pn=np.linalg.norm(pair,axis=1)
    return dict(samples=int(mask.sum()),bodies={name:dict(maximum_metres=float(p[:,i].max()),
        rms_metres=float(np.sqrt(np.mean(p[:,i]**2))),maximum_velocity_m_s=float(v[:,i].max())) for i,name in enumerate(de.NAMES)},
        pair_maximum_metres=float(pn.max()),pair_rms_metres=float(np.sqrt(np.mean(pn**2))),
        sampled_10km_1km_goal_passed=bool(p.max()<1e4 and pn.max()<1e3),free_forecast=False)


def analyse(trajectories, model, scale, reader, free_values, free_report):
    if set(trajectories)!=set(JOBS):raise ValueError('All four controlled forecasts required')
    expected=np.array([reader.states(float(t)) for t in TIMES])
    expected_rho=np.array([reader.relative(float(t)) for t in TIMES])
    expanded={};result=dict(jobs={},external={},windows={},comparisons={});arrays=dict(times=TIMES,expected_relative_m=expected_rho)
    offset=3*model.pair.second
    for name in JOBS:
        values=trajectories[name];is_ref=name.startswith('reference')
        if values.shape != (1462,81) or not np.isfinite(values).all():raise ValueError('Complete finite control inventory required')
        np.testing.assert_array_equal(values[0,:60],free_report['initial_state'][:60]);np.testing.assert_array_equal(values[0,60:],np.zeros(21))
        expanded[name]=control.expanded(values,model,TIMES,is_ref)
        result['jobs'][name]=dict(samples=1462,balances=control.balances(values,model,TIMES,scale,is_ref))
        actual,_,_=diagnostic.decoded(expanded[name],model,is_ref)
        series=dict(position_m=np.linalg.norm(actual[:,:,:3]-expected[:,:,:3],axis=2),
            velocity_m_s=np.linalg.norm(actual[:,:,3:]-expected[:,:,3:],axis=2),
            pair_vector_m=values[:,offset:offset+3]*model.units.length_m-expected_rho)
        arrays.update({name+'_'+key:v for key,v in series.items()})
        result['external'][name]=statistics(series,np.ones(1462,dtype=bool))
        result['windows'][name]={f'{x}-{y}':statistics(series,(TIMES>=x*86400)&(TIMES<=y*86400)) for x,y in annual.WINDOWS}
    a=expanded
    result['comparisons']=dict(production_refinement=diagnostic.comparison(a['nominal'],a['tight'],model),
        reference_refinement=diagnostic.comparison(a['reference_nominal'],a['reference_tight'],model,True,True),
        independent=diagnostic.comparison(a['tight'],a['reference_tight'],model,False,True))
    vectors,row=vector_decomposition(free_values[:,offset:offset+3],trajectories['tight'][:,offset:offset+3],expected_rho,model.units.length_m)
    arrays.update(vectors)
    sensitivity=max([v['pair_metres'] for v in result['comparisons'].values()]+
        [free_report['analysis']['comparisons'][key]['pair_metres'] for key in ('independent','reference_refinement')])
    row.update(sensitivity_scale_metres=sensitivity,resolved_within_controlled_model=bool(row['switch_maximum_metres']>5*sensitivity),
        real_lunar_cause_proven=False,improvement_required_for_qualification=False)
    result['intervention']=row
    result['probes']=control.probes(trajectories['tight'],model,TIMES)
    return result,arrays


def qualification(report):
    if (not report.get('complete') or report.get('samples')!=1462 or report.get('duration_seconds')!=YEAR
            or not np.array_equal(report.get('times_seconds',[]),TIMES) or set(report.get('jobs',{}))!=set(JOBS)):return False
    if report.get('prescribed_orientation_is_external') is not True:return False
    if any(report.get(key) is not False for key in ('free_forecast','runtime_modified','parameters_fitted','network_used','real_lunar_cause_proven')):return False
    a=report.get('analysis',{})
    if any(set(a.get(k,{}))!=set(JOBS) for k in ('jobs','external','windows')):return False
    if set(a.get('comparisons',{}))!=set(annual.short.LIMITS):return False
    if any(not annual.months.orbit_comparison_qualified(a['comparisons'][k],v) for k,v in annual.short.LIMITS.items()):return False
    for name in JOBS:
        b=a['jobs'][name].get('balances',{})
        if (report['jobs'][name].get('samples')!=1462 or a['jobs'][name].get('samples')!=1462 or not b.get('checks_passed')
                or b.get('closed_system') is not False or b.get('rotational_energy_included') is not False
                or b.get('source_visibility_qualified') is not False
                or set(b.get('source_integrals',{}))!={'pn2','pn_q','external_prescription'}
                or [v.get('index') for v in b.get('precision_rows',[])]!=annual.PRECISION_INDICES):return False
        if set(b.get('corrected',{}))!={'energy','momentum','angular'}:return False
        if any(not np.isfinite(v) or not 0<=v<1e-11 for v in b['corrected'].values()):return False
        if any(not 0<=v.get('maximum_scaled',np.inf)<1e-30 for v in b['precision_rows']):return False
        if set(a['windows'][name])!={f'{x}-{y}' for x,y in annual.WINDOWS}:return False
        groups=[(a['external'][name],1462)]+[(a['windows'][name][f'{x}-{y}'],int((y-x)*4)+1) for x,y in annual.WINDOWS]
        for g,count in groups:
            if g.get('samples')!=count or set(g.get('bodies',{}))!=set(de.NAMES) or g.get('free_forecast') is not False:return False
            if any(not np.isfinite(v.get(k,np.nan)) or v[k]<0 for v in g['bodies'].values()
                for k in ('maximum_metres','rms_metres','maximum_velocity_m_s')):return False
            if any(not np.isfinite(g.get(k,np.nan)) or g[k]<0 for k in ('pair_maximum_metres','pair_rms_metres')):return False
    row=a.get('intervention',{})
    if not 0<=row.get('identity_maximum_metres',np.inf)<1e-6 or row.get('real_lunar_cause_proven') is not False:return False
    if any(not np.isfinite(row.get(k,np.nan)) or row[k]<0 for k in ('switch_maximum_metres','sensitivity_scale_metres')):return False
    if row.get('resolved_within_controlled_model') != (row['switch_maximum_metres']>5*row['sensitivity_scale_metres']):return False
    probes=a.get('probes',[])
    if [v.get('index') for v in probes]!=annual.PRECISION_INDICES:return False
    for p in probes:
        if not p.get('checks_passed'):return False
        if any(not 0<=p.get(k,np.inf)<5e-10 for k in ('force_relative','torque_relative','potential_relative')):return False
        if any(not 0<=p.get(k,np.inf)<5e-12 for k in ('linear_relative','angular_relative')):return False
        if [g.get('step_rad') for g in p.get('gradients',[])]!=[1e-4,5e-5]:return False
        if any(not 0<=g.get(k,np.inf)<2e-6 for g in p['gradients'] for k in ('torque_relative','power_relative')):return False
    return all(max(p.get(k,0.) for p in probes)>1e-3 for k in
        ('missing_work_signal','wrong_work_sign_signal','missing_torque_signal','wrong_torque_sign_signal'))


def integrate_job(name, model, y, scale, output):
    if name not in JOBS:raise ValueError('Unknown control job')
    values,stats=control.integrate(model,y,TIMES,scale,name.endswith('tight'),name.startswith('reference'))
    target=Path(output)/(name+'.npz')
    if target.exists():raise ValueError('Preserve existing control output')
    np.savez_compressed(target,states=values,times=TIMES)
    return dict(**stats,samples=len(values),npz_sha256=hashes([target]).popitem()[1])


def run(output, reader_receipt, previous_report, workers=3):
    output=Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or output.exists() or output.with_suffix('.json').exists():
        raise ValueError('Use fresh .tools output; preserve failures')
    if type(workers) is not int or not 1<=workers<=3:raise ValueError('One to three processes required')
    old=free_receipt(previous_report);reader_record=json.loads(Path(reader_receipt).read_bytes())
    if not reader_record.get('checks_passed') or not reader_qualified(reader_record):raise ValueError('Qualified reader required')
    for key in ('source_sha256','input_sha256'):
        if hashes(reader_record[key])!=reader_record[key]:raise ValueError('Reader closure changed')
    model,y,scale,seed=control.initial();np.testing.assert_array_equal(y[:60],old['initial_state'][:60])
    if tuple(b.name for b in seed.bodies)!=de.NAMES:raise ValueError('Pinned ten-body order required')
    sources={str(Path(m.__file__).resolve().relative_to(ROOT)) for m in tuple(sys.modules.values()) if getattr(m,'__file__',None)
        and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(ROOT)
        and Path(m.__file__).resolve().parts[len(ROOT.parts)] in ('scripts','src')}
    source_sha=hashes(sorted(sources|{PROTOCOL,'tests/test_prescribed_lunar.py'}))
    input_sha=hashes([reader_receipt,previous_report,*[Path(previous_report).with_suffix('')/(name+'.npz') for name in annual.short.JOBS],
        de.ARCHIVE,'docs/solar-sandbox-strict-checkpoint.json',*sorted((ROOT/'src/solar_simulator/data').glob('*.json'))])
    report=dict(complete=False,checks_passed=False,source_sha256=source_sha,input_sha256=input_sha,origin=asdict(seed.origin),
        initial_state=y.tolist(),scales=scale.tolist(),times_seconds=TIMES.tolist(),duration_seconds=YEAR,jobs={},workers=workers,
        python=sys.version,numpy=np.__version__,scipy=scipy.__version__,prescribed_orientation_is_external=True,
        free_forecast=False,runtime_modified=False,parameters_fitted=False,network_used=False,real_lunar_cause_proven=False)
    output.mkdir(parents=True);start=perf_counter()
    def save():
        part=output.with_suffix('.json.part');part.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
        part.replace(output.with_suffix('.json'))
    save()
    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            pending={executor.submit(integrate_job,name,model,y,scale,output):name for name in
                ('reference_tight','reference_nominal','tight','nominal')}
            for f in as_completed(pending):
                name=pending[f];report['jobs'][name]=f.result()
                if hashes(source_sha)!=source_sha or hashes(input_sha)!=input_sha:raise ValueError('Frozen closure changed')
                save();print('Control',name,report['jobs'][name]['wall_seconds'],flush=True)
        trajectories=load_trajectories(output,report)
        free_values=annual.load_trajectories(Path(previous_report).with_suffix(''),old)['tight']
        reader,_=de.load_archive(ROOT/de.ARCHIVE)
        report['analysis'],arrays=analyse(trajectories,model,scale,reader,free_values,old)
        target=output/'diagnostic-series.npz';np.savez_compressed(target,**arrays)
        report['diagnostic_series_sha256']=hashes([target]).popitem()[1]
        if hashes(source_sha)!=source_sha or hashes(input_sha)!=input_sha:raise ValueError('Frozen closure changed')
        report.update(complete=True,samples=1462);report['checks_passed']=qualification(report)
    except BaseException as error:
        report.update(complete=False,checks_passed=False,failure=dict(type=type(error).__name__,message=str(error)));raise
    finally:report['wall_seconds']=perf_counter()-start;save()
    print('Controlled year complete',report['complete'],'checks',report['checks_passed'],flush=True)
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('output','reader-receipt','previous-report'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--workers',type=int,default=3);a=parser.parse_args()
    if not run(a.output,a.reader_receipt,a.previous_report,a.workers)['checks_passed']:raise RuntimeError('Preserved control diagnostic failure')


if __name__=='__main__':main()
