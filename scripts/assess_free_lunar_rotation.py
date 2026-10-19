"""Predeclared 32-day research forecast, separate numerical and DE441 goals."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

import numpy as np
import scipy

from scripts import free_lunar_rotation as production
from scripts import independent_free_lunar as reference
from scripts import free_lunar_diagnostics as diagnostic
from scripts import de441_reader as de
from scripts.assess_de441_reader import qualification as reader_qualified
from scripts.independent_hybrid_rotation import body_field
from scripts.newton_year import ROOT, hashes
from scripts.real_spin_scales import vector_relative
from solar_simulator.nbody_rotation import correction
from solar_simulator.orientation import lunar_rotation

PROTOCOL = 'docs/free-lunar-rotation-protocol.md'
JOBS = ('nominal','tight','reference_nominal','reference_tight','baseline')
LIMITS = dict(production_refinement=(4.,.2,1e-5,2e-7,2e-7),
    reference_refinement=(1.,.05,3e-6,1e-7,1e-7),independent=(2.,.1,5e-6,1e-7,1e-7))


def initial_bridge(model, y):
    x,_,rho,q,_ = production.unpack(y,model)
    r = diagnostic.rotation_matrix(q)
    centered = x-x[model.source]; centered[model.pair.first] = -rho
    force,torque,_ = body_field(centered,model.masses,r,model.moments,model.source,
        model.figure.bounding_radius/model.units.length_m)
    a,tau,_ = correction(centered*model.units.length_m,np.asarray(model.masses_si),model.source,model.figure,q)
    energy_unit = model.units.mass_kg*model.units.velocity_m_s**2
    actual = a*(model.units.time_s**2/model.units.length_m)*model.masses[:,None]
    force_error = vector_relative(actual-force,force)
    torque_error = vector_relative(tau/energy_unit-r@torque,r@torque)
    force_scale = np.linalg.norm(force,axis=1).sum()
    missing_reaction = float(np.linalg.norm(force[model.source])/force_scale)
    missing_torque = float(np.linalg.norm(np.cross(centered,force).sum(axis=0))/np.linalg.norm(torque))
    return dict(force_relative=force_error,torque_relative=torque_error,
        missing_reaction=missing_reaction,missing_torque=missing_torque,
        checks_passed=force_error < 5e-10 and torque_error < 5e-10 and missing_reaction > 1e-3 and missing_torque > 1e-3)


def external_metrics(values, model, times, reader):
    n = len(model.masses_si); actual,r,_ = diagnostic.decoded(values,model)
    expected = np.array([reader.states(float(t)) for t in times])
    position = np.linalg.norm(actual[:,:,:3]-expected[:,:,:3],axis=2)
    offset = 3*model.pair.second
    rho = values[:,offset:offset+3]*model.units.length_m
    pair = np.linalg.norm(rho-np.array([reader.relative(float(t)) for t in times]),axis=1)
    rotations = np.array([lunar_rotation(float(t))[0] for t in times])
    orientation = 2*np.arcsin(np.minimum(1.,np.linalg.norm(r-rotations,axis=(1,2))/(2*np.sqrt(2))))
    return dict(bodies={name:dict(maximum_metres=float(position[:,j].max()),rms_metres=float(np.sqrt(np.mean(position[:,j]**2))))
        for j,name in enumerate(de.NAMES)},pair_maximum_metres=float(pair.max()),pair_rms_metres=float(np.sqrt(np.mean(pair**2))),
        orientation_maximum_radians=float(orientation.max()),orientation_rms_radians=float(np.sqrt(np.mean(orientation**2))),
        sampled_10km_1km_goal_passed=bool(position.max() < 1e4 and pair.max() < 1e3),
        annual_accuracy_qualified=False,continuous_time_accuracy_qualified=False)


def qualification(report):
    if (not report.get('complete') or report.get('samples') != 129 or report.get('duration_seconds') != 32*86400.
            or set(report.get('jobs',{})) != set(JOBS) or set(report.get('comparisons',{})) != set(LIMITS)
            or not report.get('initial_bridge',{}).get('checks_passed')):
        return False
    for row in report['comparisons'].values():
        body = np.asarray(row.get('per_body_metres',[]))
        if body.shape != (10,) or not np.isfinite(body).all() or np.any(body < 0):return False
    for job in report['jobs'].values():
        balance = job.get('balances',{})
        if (job.get('samples') != 129 or not np.isfinite(job.get('raw_rotation_defect',np.nan))
                or job['raw_rotation_defect'] < 0 or not balance.get('checks_passed')
                or set(balance.get('source_integrals',{})) != {'pn2','pn_q','fixed_axes_torque'}
                or [r.get('index') for r in balance.get('precision_rows',[])] != list(range(0,129,16))):
            return False
        for group in ('raw','corrected'):
            if set(balance.get(group,{})) != {'energy','momentum','angular'}:return False
            if any(not np.isfinite(v) or v < 0 for v in balance[group].values()):return False
        if any(v >= 1e-11 for v in balance['corrected'].values()):return False
        if any(not np.isfinite(r['maximum_scaled']) or not 0 <= r['maximum_scaled'] < 1e-30
                for r in balance['precision_rows']):return False
    return bool(all(diagnostic.within(report['comparisons'][key],limits) for key,limits in LIMITS.items())
        and all(job['balances']['checks_passed'] and job['raw_rotation_defect'] < 1e-8 for job in report['jobs'].values()))


def run(output, reader_receipt):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or output.exists() or output.with_suffix('.json').exists():
        raise ValueError('Use fresh .tools output; preserve failures')
    receipt = json.loads(Path(reader_receipt).read_bytes())
    if not receipt.get('complete') or not receipt.get('checks_passed') or not reader_qualified(receipt):
        raise ValueError('Qualified reader receipt required')
    for key in ('source_sha256','input_sha256'):
        if hashes(receipt[key]) != receipt[key]:raise ValueError('Reader closure changed')
    model,y0,seed = production.initial(); scale = diagnostic.scales(y0,model)
    if tuple(b.name for b in seed.bodies) != de.NAMES:raise ValueError('Pinned ten-body order required')
    times = np.linspace(0.,32*86400.,129)
    sources = {str(Path(module.__file__).resolve().relative_to(ROOT)) for module in tuple(sys.modules.values())
        if getattr(module,'__file__',None) and str(module.__file__).endswith('.py')
        and Path(module.__file__).resolve().is_relative_to(ROOT)
        and Path(module.__file__).resolve().parts[len(ROOT.parts)] in ('scripts','src')}
    source_sha = hashes(sorted(sources|{PROTOCOL,'tests/test_free_lunar_rotation.py'}))
    input_sha = hashes([reader_receipt,de.ARCHIVE,'docs/solar-sandbox-strict-checkpoint.json',
        *sorted((ROOT/'src/solar_simulator/data').glob('*.json'))])
    report = dict(complete=False,checks_passed=False,source_sha256=source_sha,input_sha256=input_sha,
        origin=asdict(seed.origin),masses_kg=list(model.masses_si),moments_kg_m2=list(model.figure.moments),
        units=asdict(model.units),spin_scale_SI=float(np.linalg.norm(model.spin_si)),
        initial_state=y0.tolist(),scales=scale.tolist(),times_seconds=times.tolist(),duration_seconds=float(times[-1]),
        python=sys.version,numpy=np.__version__,scipy=scipy.__version__,jobs={},comparisons={},
        initial_bridge=initial_bridge(model,y0),runtime_modified=False,parameters_fitted=False,
        future_orientation_in_rhs=False,physical_PN_lunar_mapping_certified=False,
        annual_spin_forecast_qualified=False,ten_body_source_visibility_requalified=False,
        network_used=False)
    output.mkdir(parents=True)
    def save():output.with_suffix('.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    trajectories = {}; save()
    try:
        for name in JOBS:
            is_reference = name.startswith('reference'); tight = name.endswith('tight'); active = name != 'baseline'
            if is_reference:
                values,stats = reference.integrate(model,y0,times,scale,tight)
                r = values[:,6*len(model.masses_si):6*len(model.masses_si)+9].reshape(-1,3,3)
                defect = max(np.linalg.norm(np.swapaxes(r,1,2)@r-np.eye(3),axis=(1,2)).max(),abs(np.linalg.det(r)-1).max())
            else:
                values,stats = production.integrate(model,y0,times,scale,tight,active)
                defect = abs(np.linalg.norm(values[:,6*len(model.masses_si):6*len(model.masses_si)+4],axis=1)-1).max()
            trajectories[name] = values
            target = output/(name+'.npz'); np.savez_compressed(target,states=values,times=times)
            report['jobs'][name] = dict(**stats,samples=len(values),npz_sha256=hashes([target]).popitem()[1],
                raw_rotation_defect=float(defect),balances=diagnostic.balances(values,model,scale,is_reference,active))
            save(); print(name,'seconds',stats['wall_seconds'],'balances',report['jobs'][name]['balances']['checks_passed'],flush=True)
        a = trajectories
        report['comparisons'] = dict(production_refinement=diagnostic.comparison(a['nominal'],a['tight'],model),
            reference_refinement=diagnostic.comparison(a['reference_nominal'],a['reference_tight'],model,True,True),
            independent=diagnostic.comparison(a['tight'],a['reference_tight'],model,False,True))
        report['model_difference'] = diagnostic.comparison(a['tight'],a['baseline'],model)
        # Future DE441 states/attitudes are first consumed after all free integrations.
        reader,_ = de.load_archive(ROOT/de.ARCHIVE)
        report['external'] = {name:external_metrics(a[name],model,times,reader) for name in ('baseline','nominal','tight')}
        report['residual_increases'] = {name:report['external']['tight']['bodies'][name]['maximum_metres']-
            report['external']['baseline']['bodies'][name]['maximum_metres'] for name in de.NAMES}
        if hashes(source_sha) != source_sha or hashes(input_sha) != input_sha:raise ValueError('Frozen closure changed')
        report.update(complete=True,samples=129); report['checks_passed'] = qualification(report); save()
    except BaseException as error:
        report.update(complete=False,checks_passed=False,failure=dict(type=type(error).__name__,message=str(error))); save(); raise
    print('Free research complete',report['complete'],'numerical checks',report['checks_passed'],flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True); parser.add_argument('--reader-receipt',type=Path,required=True)
    args = parser.parse_args()
    if not run(args.output,args.reader_receipt)['checks_passed']:raise RuntimeError('Preserved research qualification failure')


if __name__ == '__main__':main()
