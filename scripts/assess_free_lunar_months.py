"""Unchanged free-rotor equations over 96 days; numerical and model errors separate."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
import scipy

from scripts import assess_free_lunar_rotation as short
from scripts import free_lunar_rotation as production
from scripts import independent_free_lunar as reference
from scripts import free_lunar_diagnostics as diagnostic
from scripts import de441_reader as de
from scripts.assess_de441_reader import qualification as reader_qualified
from scripts.newton_year import ROOT, hashes

PROTOCOL = 'docs/free-lunar-months-protocol.md'
DAY = 86400.
TIMES = np.arange(385,dtype=float)*21600.
PREFIX_LIMITS = (.1,.01,1e-6,1e-9,1e-9)


def validate_grid(times):
    if not np.array_equal(np.asarray(times),TIMES):
        raise ValueError('All 385 exact six-hour epochs over 96 days are required')


def body_angles(rotations, relative):
    """Sub-Earth principal-axis longitude/latitude; no Euler-angle convention."""
    r,rho = np.asarray(rotations),np.asarray(relative)
    if (rho.ndim != 2 or rho.shape[1:] != (3,) or r.shape != (len(rho),3,3)
            or not np.isfinite(r).all() or not np.isfinite(rho).all()):
        raise ValueError('Finite matching attitude and Moon-minus-Earth vectors required')
    distance = np.linalg.norm(rho,axis=1)
    if np.any(distance == 0):raise ValueError('Sub-Earth direction requires distinct centres')
    body = np.einsum('tji,tj->ti',r,-rho/distance[:,None])
    if np.any(np.linalg.norm(body,axis=1) == 0):raise ValueError('Nonzero body direction required')
    return np.c_[np.unwrap(np.arctan2(body[:,1],body[:,0])),
        np.arctan2(body[:,2],np.hypot(body[:,0],body[:,1]))]


def circular_difference(first, second):
    delta = np.asarray(first)-np.asarray(second)
    if not np.isfinite(delta).all():raise ValueError('Finite angular differences required')
    return np.arctan2(np.sin(delta),np.cos(delta))


def external_series(values, model, times, reader, is_reference=False):
    validate_grid(times)
    actual,r,_ = diagnostic.decoded(values,model,is_reference)
    if actual.shape != (385,10,6):raise ValueError('Complete ten-body forecast required')
    expected = np.array([reader.states(float(t)) for t in times])
    offset = 3*model.pair.second
    rho = values[:,offset:offset+3]*model.units.length_m
    expected_rho = np.array([reader.relative(float(t)) for t in times])
    # Attitude data are comparison inputs only, outside every free RHS.
    rotations = np.array([short.lunar_rotation(float(t))[0] for t in times])
    angles,expected_angles = body_angles(r,rho),body_angles(rotations,expected_rho)
    return dict(position_m=np.linalg.norm(actual[:,:,:3]-expected[:,:,:3],axis=2),
        velocity_m_s=np.linalg.norm(actual[:,:,3:]-expected[:,:,3:],axis=2),
        pair_m=np.linalg.norm(rho-expected_rho,axis=1),
        orientation_rad=2*np.arcsin(np.minimum(1.,np.linalg.norm(r-rotations,axis=(1,2))/(2*np.sqrt(2)))),
        subearth_angles_rad=angles,subearth_residual_rad=circular_difference(angles,expected_angles))


def series_statistics(series, mask):
    mask = np.asarray(mask)
    if mask.shape != (385,) or mask.dtype != bool or not mask.any():raise ValueError('Nonempty explicit epoch mask required')
    expected_shapes = dict(position_m=(385,10),velocity_m_s=(385,10),pair_m=(385,),orientation_rad=(385,),
        subearth_angles_rad=(385,2),subearth_residual_rad=(385,2))
    if set(series) != set(expected_shapes) or any(np.shape(series[k]) != shape or not np.isfinite(series[k]).all()
            for k,shape in expected_shapes.items()):raise ValueError('All finite external channels required')
    p,v,pair,orientation,angles,residual = (series[k][mask] for k in expected_shapes)
    return dict(samples=int(mask.sum()),
        bodies={name:dict(maximum_metres=float(p[:,i].max()),rms_metres=float(np.sqrt(np.mean(p[:,i]**2))),
            maximum_velocity_m_s=float(v[:,i].max())) for i,name in enumerate(de.NAMES)},
        pair_maximum_metres=float(pair.max()),pair_rms_metres=float(np.sqrt(np.mean(pair**2))),
        orientation_maximum_radians=float(orientation.max()),orientation_rms_radians=float(np.sqrt(np.mean(orientation**2))),
        subearth_longitude_span_rad=float(np.ptp(angles[:,0])),subearth_latitude_span_rad=float(np.ptp(angles[:,1])),
        subearth_residual_max_rad=np.max(abs(residual),axis=0).tolist(),
        subearth_residual_rms_rad=np.sqrt(np.mean(residual**2,axis=0)).tolist(),
        sampled_10km_1km_goal_passed=bool(p.max() < 1e4 and pair.max() < 1e3),
        annual_accuracy_qualified=False,continuous_time_accuracy_qualified=False)


def previous_receipt(path):
    path = Path(path).resolve(); row = json.loads(path.read_bytes())
    if not row.get('checks_passed') or not short.qualification(row):raise ValueError('Qualified original 32-day receipt required')
    for key in ('source_sha256','input_sha256'):
        if hashes(row[key]) != row[key]:raise ValueError('Original 32-day closure changed')
    for name in short.JOBS:
        target = path.with_suffix('')/(name+'.npz')
        if hashes([target]).popitem()[1] != row['jobs'][name]['npz_sha256']:raise ValueError('Original 32-day trajectory changed')
    return row


def load_trajectories(directory, report):
    values = {}
    for name in short.JOBS:
        path = Path(directory)/(name+'.npz')
        if hashes([path]).popitem()[1] != report['jobs'][name]['npz_sha256']:raise ValueError('Forecast trajectory SHA mismatch')
        with np.load(path,allow_pickle=False) as packet:
            validate_grid(packet['times']); values[name] = packet['states'].copy(order='K')
        size = 6*10+(33 if name.startswith('reference') else 28)
        if values[name].shape != (385,size) or not np.isfinite(values[name]).all():raise ValueError('Incomplete forecast trajectory')
    return values


def analyse(trajectories, model, scale, times, reader, previous_report):
    validate_grid(times)
    if set(trajectories) != set(short.JOBS):raise ValueError('All five forecasts are required')
    result = dict(jobs={},external={},prefixes={},windows={},previous32={},comparisons={})
    series_arrays = dict(times=times)
    for name,values in trajectories.items():
        is_reference = name.startswith('reference'); n = len(model.masses_si)
        if values.shape != (385,6*n+(33 if is_reference else 28)) or not np.isfinite(values).all():
            raise ValueError('Incomplete or nonfinite 96-day state inventory')
        if is_reference:
            r = values[:,6*n:6*n+9].reshape(-1,3,3)
            defect = max(np.linalg.norm(np.swapaxes(r,1,2)@r-np.eye(3),axis=(1,2)).max(),abs(np.linalg.det(r)-1).max())
        else:
            defect = abs(np.linalg.norm(values[:,6*n:6*n+4],axis=1)-1).max()
        result['jobs'][name] = dict(samples=385,raw_rotation_defect=float(defect),
            balances=diagnostic.balances(values,model,scale,is_reference,name != 'baseline'))
        series = external_series(values,model,times,reader,is_reference)
        series_arrays.update({name+'_'+key:val for key,val in series.items()})
        result['external'][name] = series_statistics(series,np.ones(385,dtype=bool))
        result['prefixes'][name] = {str(day):series_statistics(series,times <= day*DAY) for day in (32,64,96)}
        result['windows'][name] = {f'{start}-{start+32}':series_statistics(series,(times >= start*DAY)&(times <= (start+32)*DAY))
            for start in (0,32,64)}
        if previous_report is not None:
            old_path = Path(previous_report).with_suffix('')/(name+'.npz')
            with np.load(old_path,allow_pickle=False) as old:
                np.testing.assert_array_equal(old['times'],times[:129]); earlier = old['states']
            row = diagnostic.comparison(values[:129],earlier,model,is_reference,is_reference)
            row['bitexact_rows'] = int(np.all(values[:129] == earlier,axis=1).sum())
            row['checks_passed'] = diagnostic.within(row,PREFIX_LIMITS)
            result['previous32'][name] = row
    a = trajectories
    result['comparisons'] = dict(production_refinement=diagnostic.comparison(a['nominal'],a['tight'],model),
        reference_refinement=diagnostic.comparison(a['reference_nominal'],a['reference_tight'],model,True,True),
        independent=diagnostic.comparison(a['tight'],a['reference_tight'],model,False,True))
    result['model_difference_same_tolerances'] = diagnostic.comparison(a['nominal'],a['baseline'],model)
    result['residual_changes_same_tolerances'] = {name:result['external']['nominal']['bodies'][name]['maximum_metres']-
        result['external']['baseline']['bodies'][name]['maximum_metres'] for name in de.NAMES}
    return result,series_arrays


def orbit_comparison_qualified(row, limits):
    body = np.asarray(row.get('per_body_metres',[]))
    return bool(body.shape == (10,) and np.isfinite(body).all() and np.all(body >= 0)
        and float(body.max()) == row.get('all_body_metres') and diagnostic.within(row,limits))


def qualification(report):
    if (not report.get('complete') or report.get('samples') != 385 or not np.array_equal(report.get('times_seconds',[]),TIMES)
            or report.get('duration_seconds') != 96*DAY or not report.get('initial_bridge',{}).get('checks_passed')):return False
    a = report.get('analysis',{})
    if (any(set(a.get(key,{})) != set(short.JOBS) for key in ('jobs','external','prefixes','windows','previous32'))
            or set(a.get('comparisons',{})) != set(short.LIMITS)):return False
    for key,limits in short.LIMITS.items():
        row = a['comparisons'][key]
        if not orbit_comparison_qualified(row,limits):return False
    for name in short.JOBS:
        job = a['jobs'][name]; balance = job.get('balances',{})
        if (job.get('samples') != 385 or not 0 <= job.get('raw_rotation_defect',np.inf) < 1e-8
                or not balance.get('checks_passed') or set(balance.get('source_integrals',{})) != {'pn2','pn_q','fixed_axes_torque'}
                or [r.get('index') for r in balance.get('precision_rows',[])] != list(range(0,385,48))
                or not orbit_comparison_qualified(a['previous32'][name],PREFIX_LIMITS)):return False
        if set(balance.get('corrected',{})) != {'energy','momentum','angular'}:return False
        if any(not np.isfinite(v) or not 0 <= v < 1e-11 for v in balance['corrected'].values()):return False
        if any(not 0 <= row.get('maximum_scaled',np.inf) < 1e-30 for row in balance['precision_rows']):return False
        groups = [a['external'][name]]
        if set(a['prefixes'][name]) != {'32','64','96'} or set(a['windows'][name]) != {'0-32','32-64','64-96'}:return False
        groups += list(a['prefixes'][name].values())+list(a['windows'][name].values())
        if [a['prefixes'][name][str(day)].get('samples') for day in (32,64,96)] != [129,257,385]:return False
        if any(v.get('samples') != 129 for v in a['windows'][name].values()):return False
        if a['external'][name].get('samples') != 385:return False
        for group in groups:
            if set(group.get('bodies',{})) != set(de.NAMES):return False
            if group.get('annual_accuracy_qualified') is not False or group.get('continuous_time_accuracy_qualified') is not False:return False
            if any(not np.isfinite(row.get(k,np.nan)) or row[k] < 0 for row in group['bodies'].values()
                    for k in ('maximum_metres','rms_metres','maximum_velocity_m_s')):return False
            if any(not np.isfinite(group.get(k,np.nan)) or group[k] < 0 for k in
                    ('pair_maximum_metres','pair_rms_metres','orientation_maximum_radians','subearth_longitude_span_rad','subearth_latitude_span_rad')):return False
    return True


def run(output, reader_receipt, previous_report):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or output.exists() or output.with_suffix('.json').exists():
        raise ValueError('Use fresh .tools output; preserve failures')
    receipt = json.loads(Path(reader_receipt).read_bytes()); old = previous_receipt(previous_report)
    if not receipt.get('complete') or not receipt.get('checks_passed') or not reader_qualified(receipt):raise ValueError('Qualified reader required')
    for key in ('source_sha256','input_sha256'):
        if hashes(receipt[key]) != receipt[key]:raise ValueError('Reader closure changed')
    model,y0,seed = production.initial(); scale = diagnostic.scales(y0,model)
    if tuple(b.name for b in seed.bodies) != de.NAMES:raise ValueError('Pinned ten-body names/order required')
    np.testing.assert_array_equal(y0,old['initial_state']); np.testing.assert_array_equal(TIMES[:129],old['times_seconds'])
    sources = {str(Path(m.__file__).resolve().relative_to(ROOT)) for m in tuple(sys.modules.values())
        if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(ROOT)
        and Path(m.__file__).resolve().parts[len(ROOT.parts)] in ('scripts','src')}
    source_sha = hashes(sorted(sources|{PROTOCOL,'tests/test_free_lunar_months.py'}))
    prior_paths = [Path(previous_report).with_suffix('')/(name+'.npz') for name in short.JOBS]
    input_sha = hashes([reader_receipt,previous_report,*prior_paths,de.ARCHIVE,'docs/solar-sandbox-strict-checkpoint.json',
        *sorted((ROOT/'src/solar_simulator/data').glob('*.json'))])
    report = dict(complete=False,checks_passed=False,source_sha256=source_sha,input_sha256=input_sha,
        origin=asdict(seed.origin),initial_state=y0.tolist(),scales=scale.tolist(),times_seconds=TIMES.tolist(),
        duration_seconds=96*DAY,python=sys.version,numpy=np.__version__,scipy=scipy.__version__,jobs={},
        initial_bridge=short.initial_bridge(model,y0),runtime_modified=False,parameters_fitted=False,
        previous_trajectories_used_for_propagation=False,future_orientation_in_rhs=False,
        annual_accuracy_qualified=False,physical_PN_lunar_mapping_certified=False,network_used=False)
    output.mkdir(parents=True); start = perf_counter()
    def save():output.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    values = {}; save()
    try:
        for name in short.JOBS:
            is_reference = name.startswith('reference'); tight = name.endswith('tight')
            if is_reference:trajectory,stats = reference.integrate(model,y0,TIMES,scale,tight)
            else:trajectory,stats = production.integrate(model,y0,TIMES,scale,tight,name != 'baseline')
            values[name] = trajectory; target = output/(name+'.npz')
            np.savez_compressed(target,states=trajectory,times=TIMES)
            report['jobs'][name] = dict(**stats,npz_sha256=hashes([target]).popitem()[1],samples=len(trajectory))
            save(); print('96day',name,'seconds',stats['wall_seconds'],flush=True)
        reader,_ = de.load_archive(ROOT/de.ARCHIVE)
        report['analysis'],series = analyse(values,model,scale,TIMES,reader,previous_report)
        target = output/'diagnostic-series.npz'; np.savez_compressed(target,**series)
        report['diagnostic_series_sha256'] = hashes([target]).popitem()[1]
        if hashes(source_sha) != source_sha or hashes(input_sha) != input_sha:raise ValueError('Frozen closure changed')
        report.update(complete=True,samples=385); report['checks_passed'] = qualification(report)
    except BaseException as error:
        report.update(complete=False,checks_passed=False,failure=dict(type=type(error).__name__,message=str(error))); raise
    finally:report['wall_seconds'] = perf_counter()-start; save()
    print('96day complete',report['complete'],'checks',report['checks_passed'],flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('output','reader-receipt','previous-report'):parser.add_argument('--'+key,type=Path,required=True)
    args = parser.parse_args()
    if not run(args.output,args.reader_receipt,args.previous_report)['checks_passed']:raise RuntimeError('Preserved 96day numerical failure')


if __name__ == '__main__':main()
