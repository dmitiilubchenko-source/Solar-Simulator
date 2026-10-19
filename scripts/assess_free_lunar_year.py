"""One Julian year of the unchanged research rotor; no runtime registration."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import perf_counter

import numpy as np
import scipy

from scripts import assess_free_lunar_months as months
from scripts import assess_free_lunar_rotation as short
from scripts import free_lunar_rotation as production
from scripts import independent_free_lunar as reference
from scripts import free_lunar_diagnostics as diagnostic
from scripts import de441_reader as de
from scripts.assess_de441_reader import qualification as reader_qualified
from scripts.newton_year import ROOT, YEAR, hashes

PROTOCOL = 'docs/free-lunar-year-protocol.md'
TIMES = np.arange(1462,dtype=float)*21600.
PREFIX_DAYS = (32.,64.,96.,192.,288.,365.25)
WINDOWS = ((0.,96.),(96.,192.),(192.,288.),(288.,365.25))
PRECISION_INDICES = np.linspace(0,1461,9,dtype=int).tolist()


def validate_grid(times):
    if not np.array_equal(np.asarray(times),TIMES):
        raise ValueError('All 1462 exact six-hour epochs over 365.25 days required')


def previous_receipt(path):
    """Validate both current postprocessing and archived executed propagation."""
    path = Path(path).resolve(); row = json.loads(path.read_bytes())
    if not row.get('checks_passed') or not months.qualification(row):
        raise ValueError('Qualified complete 96-day receipt required')
    for key in ('source_sha256','input_sha256'):
        if hashes(row[key]) != row[key]:raise ValueError('96-day closure changed')
    archives = row.get('propagation_source_archives',{})
    for name,digest in row.get('propagation_source_sha256',row['source_sha256']).items():
        if hashes([archives.get(name,name)]).popitem()[1] != digest:
            raise ValueError('96-day executed propagation changed')
    months.load_trajectories(path.with_suffix(''),row)
    return row


def load_trajectories(directory, report):
    if set(report.get('jobs',{})) != set(short.JOBS):raise ValueError('All five job receipts required')
    values = {}
    for name in short.JOBS:
        target = Path(directory)/(name+'.npz')
        if hashes([target]).popitem()[1] != report['jobs'][name]['npz_sha256']:
            raise ValueError('Annual forecast SHA mismatch')
        with np.load(target,allow_pickle=False) as packet:
            if set(packet.files) != {'times','states'}:raise ValueError('Exact trajectory channels required')
            validate_grid(packet['times']); values[name] = packet['states'].copy(order='K')
        size = 93 if name.startswith('reference') else 88
        if values[name].shape != (1462,size) or not np.isfinite(values[name]).all():
            raise ValueError('Complete finite annual trajectory required')
    return values


def external_series(values, model, reader, is_reference=False):
    actual,r,_ = diagnostic.decoded(values,model,is_reference)
    if actual.shape != (1462,10,6):raise ValueError('Complete ten-body annual forecast required')
    expected = np.array([reader.states(float(t)) for t in TIMES])
    offset = 3*model.pair.second
    rho = values[:,offset:offset+3]*model.units.length_m
    expected_rho = np.array([reader.relative(float(t)) for t in TIMES])
    rotations = np.array([short.lunar_rotation(float(t))[0] for t in TIMES])
    angles = months.body_angles(r,rho)
    expected_angles = months.body_angles(rotations,expected_rho)
    return dict(position_m=np.linalg.norm(actual[:,:,:3]-expected[:,:,:3],axis=2),
        velocity_m_s=np.linalg.norm(actual[:,:,3:]-expected[:,:,3:],axis=2),
        pair_m=np.linalg.norm(rho-expected_rho,axis=1),
        orientation_rad=2*np.arcsin(np.minimum(1.,np.linalg.norm(r-rotations,axis=(1,2))/(2*np.sqrt(2)))),
        subearth_angles_rad=angles,subearth_residual_rad=months.circular_difference(angles,expected_angles))


def series_statistics(series, mask):
    shapes = dict(position_m=(1462,10),velocity_m_s=(1462,10),pair_m=(1462,),orientation_rad=(1462,),
        subearth_angles_rad=(1462,2),subearth_residual_rad=(1462,2))
    mask = np.asarray(mask)
    if mask.shape != (1462,) or mask.dtype != bool or not mask.any():raise ValueError('Nonempty annual epoch mask required')
    if set(series) != set(shapes) or any(np.shape(series[k]) != shape or not np.isfinite(series[k]).all()
            for k,shape in shapes.items()):raise ValueError('All finite annual channels and ten bodies required')
    p,v,pair,orientation,angles,residual = (series[k][mask] for k in shapes)
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


def analyse(trajectories, model, scale, reader, previous_directory, previous_report):
    if set(trajectories) != set(short.JOBS):raise ValueError('All five annual forecasts required')
    prior = months.load_trajectories(previous_directory,previous_report)
    result = dict(jobs={},external={},prefixes={},windows={},previous96={},comparisons={})
    arrays = dict(times=TIMES)
    for name in short.JOBS:
        values = trajectories[name]; is_reference = name.startswith('reference'); n = len(model.masses_si)
        if values.shape != (1462,6*n+(33 if is_reference else 28)) or not np.isfinite(values).all():
            raise ValueError('Incomplete or nonfinite annual state inventory')
        expected_initial = reference.initial(np.asarray(previous_report['initial_state']),model) if is_reference else previous_report['initial_state']
        np.testing.assert_array_equal(values[0],expected_initial)
        if is_reference:
            r = values[:,6*n:6*n+9].reshape(-1,3,3)
            defect = max(np.linalg.norm(np.swapaxes(r,1,2)@r-np.eye(3),axis=(1,2)).max(),abs(np.linalg.det(r)-1).max())
        else:defect = abs(np.linalg.norm(values[:,6*n:6*n+4],axis=1)-1).max()
        result['jobs'][name] = dict(samples=1462,raw_rotation_defect=float(defect),
            balances=diagnostic.balances(values,model,scale,is_reference,name != 'baseline'))
        series = external_series(values,model,reader,is_reference)
        arrays.update({name+'_'+key:val for key,val in series.items()})
        result['external'][name] = series_statistics(series,np.ones(1462,dtype=bool))
        result['prefixes'][name] = {str(day):series_statistics(series,TIMES <= day*86400.) for day in PREFIX_DAYS}
        result['windows'][name] = {f'{start}-{end}':series_statistics(series,(TIMES >= start*86400.)&(TIMES <= end*86400.))
            for start,end in WINDOWS}
        row = diagnostic.comparison(values[:385],prior[name],model,is_reference,is_reference)
        row['bitexact_rows'] = int(np.all(values[:385] == prior[name],axis=1).sum())
        row['checks_passed'] = months.orbit_comparison_qualified(row,months.PREFIX_LIMITS)
        result['previous96'][name] = row
    a = trajectories
    result['comparisons'] = dict(production_refinement=diagnostic.comparison(a['nominal'],a['tight'],model),
        reference_refinement=diagnostic.comparison(a['reference_nominal'],a['reference_tight'],model,True,True),
        independent=diagnostic.comparison(a['tight'],a['reference_tight'],model,False,True))
    result['model_difference_same_tolerances'] = diagnostic.comparison(a['nominal'],a['baseline'],model)
    result['residual_changes_same_tolerances'] = {name:result['external']['nominal']['bodies'][name]['maximum_metres']-
        result['external']['baseline']['bodies'][name]['maximum_metres'] for name in de.NAMES}
    return result,arrays


def qualification(report):
    if (not report.get('complete') or report.get('samples') != 1462 or report.get('duration_seconds') != YEAR
            or not np.array_equal(report.get('times_seconds',[]),TIMES)
            or set(report.get('jobs',{})) != set(short.JOBS)
            or not report.get('initial_bridge',{}).get('checks_passed')):return False
    if any(report.get(key) is not False for key in ('runtime_modified','parameters_fitted',
            'previous_trajectories_used_for_propagation','future_orientation_in_rhs',
            'annual_accuracy_qualified','physical_PN_lunar_mapping_certified','network_used')):return False
    a = report.get('analysis',{})
    if (any(set(a.get(key,{})) != set(short.JOBS) for key in ('jobs','external','prefixes','windows','previous96'))
            or set(a.get('comparisons',{})) != set(short.LIMITS)):return False
    if any(not months.orbit_comparison_qualified(a['comparisons'][key],limits) for key,limits in short.LIMITS.items()):return False
    for name in short.JOBS:
        job = a['jobs'][name]; balance = job.get('balances',{})
        if (report['jobs'][name].get('samples') != 1462 or job.get('samples') != 1462
                or not 0 <= job.get('raw_rotation_defect',np.inf) < 1e-8 or not balance.get('checks_passed')
                or balance.get('source_visibility_qualified') is not False
                or set(balance.get('source_integrals',{})) != {'pn2','pn_q','fixed_axes_torque'}
                or [r.get('index') for r in balance.get('precision_rows',[])] != PRECISION_INDICES
                or not months.orbit_comparison_qualified(a['previous96'][name],months.PREFIX_LIMITS)):return False
        for key in ('raw','corrected'):
            if set(balance.get(key,{})) != {'energy','momentum','angular'}:return False
            if any(not np.isfinite(v) or v < 0 for v in balance[key].values()):return False
        if any(v >= 1e-11 for v in balance['corrected'].values()):return False
        if any(not 0 <= row.get('maximum_scaled',np.inf) < 1e-30 for row in balance['precision_rows']):return False
        if set(a['prefixes'][name]) != {str(day) for day in PREFIX_DAYS}:return False
        if set(a['windows'][name]) != {f'{x}-{y}' for x,y in WINDOWS}:return False
        groups = [(a['external'][name],1462)]
        groups += [(a['prefixes'][name][str(day)],int(day*4)+1) for day in PREFIX_DAYS]
        groups += [(a['windows'][name][f'{x}-{y}'],int((y-x)*4)+1) for x,y in WINDOWS]
        for group,count in groups:
            if (group.get('samples') != count or set(group.get('bodies',{})) != set(de.NAMES)
                    or group.get('annual_accuracy_qualified') is not False
                    or group.get('continuous_time_accuracy_qualified') is not False):return False
            if any(not np.isfinite(row.get(k,np.nan)) or row[k] < 0 for row in group['bodies'].values()
                    for k in ('maximum_metres','rms_metres','maximum_velocity_m_s')):return False
            if any(not np.isfinite(group.get(k,np.nan)) or group[k] < 0 for k in
                    ('pair_maximum_metres','pair_rms_metres','orientation_maximum_radians','orientation_rms_radians',
                     'subearth_longitude_span_rad','subearth_latitude_span_rad')):return False
            if any(np.shape(group.get(k)) != (2,) or not np.isfinite(group[k]).all() or np.any(np.asarray(group[k]) < 0)
                    for k in ('subearth_residual_max_rad','subearth_residual_rms_rad')):return False
    return True


def integrate_job(name, model, y0, scale, output):
    """One process owns one continuous forecast and its immutable NPZ."""
    if name not in short.JOBS:raise ValueError('Unknown annual job')
    if name.startswith('reference'):values,stats = reference.integrate(model,y0,TIMES,scale,name.endswith('tight'))
    else:values,stats = production.integrate(model,y0,TIMES,scale,name.endswith('tight'),name != 'baseline')
    target = Path(output)/(name+'.npz')
    if target.exists():raise ValueError('Preserve existing forecast')
    np.savez_compressed(target,states=values,times=TIMES)
    return dict(**stats,npz_sha256=hashes([target]).popitem()[1],samples=len(values))


def run(output, reader_receipt, previous_report, workers=3):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or output.exists() or output.with_suffix('.json').exists():
        raise ValueError('Use fresh .tools output; preserve failures')
    if type(workers) is not int or not 1 <= workers <= 3:raise ValueError('One to three worker processes required')
    old = previous_receipt(previous_report)
    receipt = json.loads(Path(reader_receipt).read_bytes())
    if not receipt.get('complete') or not receipt.get('checks_passed') or not reader_qualified(receipt):
        raise ValueError('Qualified reader required')
    for key in ('source_sha256','input_sha256'):
        if hashes(receipt[key]) != receipt[key]:raise ValueError('Reader closure changed')
    model,y0,seed = production.initial(); scale = diagnostic.scales(y0,model)
    if tuple(b.name for b in seed.bodies) != de.NAMES:raise ValueError('Pinned ten-body order required')
    np.testing.assert_array_equal(y0,old['initial_state']); np.testing.assert_array_equal(scale,old['scales'])
    np.testing.assert_array_equal(TIMES[:385],old['times_seconds'])
    sources = {str(Path(m.__file__).resolve().relative_to(ROOT)) for m in tuple(sys.modules.values())
        if getattr(m,'__file__',None) and str(m.__file__).endswith('.py') and Path(m.__file__).resolve().is_relative_to(ROOT)
        and Path(m.__file__).resolve().parts[len(ROOT.parts)] in ('scripts','src')}
    source_sha = hashes(sorted(sources|{PROTOCOL,'tests/test_free_lunar_year.py'}))
    prior_paths = [Path(previous_report).with_suffix('')/(name+'.npz') for name in short.JOBS]
    input_sha = hashes([reader_receipt,previous_report,*prior_paths,de.ARCHIVE,'docs/solar-sandbox-strict-checkpoint.json',
        *sorted((ROOT/'src/solar_simulator/data').glob('*.json'))])
    report = dict(complete=False,checks_passed=False,source_sha256=source_sha,input_sha256=input_sha,
        origin=asdict(seed.origin),masses_kg=list(model.masses_si),moments_kg_m2=list(model.figure.moments),
        units=asdict(model.units),spin_scale_SI=float(np.linalg.norm(model.spin_si)),
        initial_state=y0.tolist(),scales=scale.tolist(),times_seconds=TIMES.tolist(),duration_seconds=YEAR,
        python=sys.version,numpy=np.__version__,scipy=scipy.__version__,jobs={},workers=workers,
        initial_bridge=short.initial_bridge(model,y0),runtime_modified=False,parameters_fitted=False,
        previous_trajectories_used_for_propagation=False,future_orientation_in_rhs=False,
        annual_accuracy_qualified=False,physical_PN_lunar_mapping_certified=False,network_used=False)
    output.mkdir(parents=True); start = perf_counter()
    def save():
        part = output.with_suffix('.json.part')
        part.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
        part.replace(output.with_suffix('.json'))
    save()
    try:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Longest 96-day jobs first; equations and each job's arithmetic unchanged.
            order = ('reference_tight','reference_nominal','tight','baseline','nominal')
            pending = {executor.submit(integrate_job,name,model,y0,scale,output):name for name in order}
            for future in as_completed(pending):
                name = pending[future]; report['jobs'][name] = future.result()
                if hashes(source_sha) != source_sha or hashes(input_sha) != input_sha:raise ValueError('Frozen closure changed')
                save(); print('Year',name,'seconds',report['jobs'][name]['wall_seconds'],flush=True)
        # No future ephemeris/orientation readout until all five forecasts exist.
        trajectories = load_trajectories(output,report); reader,_ = de.load_archive(ROOT/de.ARCHIVE)
        report['analysis'],arrays = analyse(trajectories,model,scale,reader,Path(previous_report).with_suffix(''),old)
        target = output/'diagnostic-series.npz'; np.savez_compressed(target,**arrays)
        report['diagnostic_series_sha256'] = hashes([target]).popitem()[1]
        if hashes(source_sha) != source_sha or hashes(input_sha) != input_sha:raise ValueError('Frozen closure changed')
        report.update(complete=True,samples=1462); report['checks_passed'] = qualification(report)
    except BaseException as error:
        report.update(complete=False,checks_passed=False,failure=dict(type=type(error).__name__,message=str(error)))
        raise
    finally:report['wall_seconds'] = perf_counter()-start; save()
    print('Year complete',report['complete'],'numerical checks',report['checks_passed'],flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('output','reader-receipt','previous-report'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--workers',type=int,default=3)
    args = parser.parse_args()
    if not run(args.output,args.reader_receipt,args.previous_report,args.workers)['checks_passed']:
        raise RuntimeError('Preserved annual numerical failure')


if __name__ == '__main__':main()
