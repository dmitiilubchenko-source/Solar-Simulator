"""Frozen-source 3D current/cotangent/tensor snapshot audit, no fluid dynamics."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy
from scipy.integrate import solve_ivp

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import harmonic_sphere as harmonic
from scripts import chart_current as current
from scripts import independent_harmonic_reference as radial_reference
from scripts import independent_current_reference as reference
from scripts.independent_conventions_reference import gauss_nodes
from scripts.assess_metric_spin import failures

POLICY='scripts/chart-current-policy.json'
USED_POLICIES=(POLICY,'scripts/metric-spin-policy.json')


def source_hashes():
    paths={p for folder in ('src','scripts','tests') for p in (ROOT/folder).rglob('*.py')}
    paths.update(ROOT/name for name in USED_POLICIES)
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


LOADED_SOURCES=source_hashes()


def check_sources():
    if source_hashes()!=LOADED_SOURCES:raise ValueError('Scientific sources changed since module initialization')


def primary_hashes(policy):
    result={}
    for name,expected in policy['primary_sha256'].items():
        p=ROOT/name
        if not p.is_file():raise FileNotFoundError('Primary scientific artifact unavailable: '+name)
        actual=hashlib.sha256(p.read_bytes()).hexdigest()
        if actual!=expected:raise ValueError('Pinned primary scientific artifact changed: '+name)
        result[name]=actual
    return result


def relative(actual,expected):
    scale=np.linalg.norm(np.asarray(expected))
    if not np.isfinite(scale) or scale<=0:raise ValueError('Nonzero finite reference scale required')
    return float(np.linalg.norm(np.asarray(actual)-expected)/scale)


def audit(*,work=None,output=None):
    work=Path(work or ROOT/'.tools/rotation107').resolve();output=Path(output or ROOT/'docs/chart-current-validation.json').resolve()
    if not work.is_relative_to(ROOT) or not output.is_relative_to(ROOT):raise ValueError('Outputs must be inside project')
    if work.exists() or output.exists():raise FileExistsError('Fresh work/output paths required')
    check_sources();code_sources=source_hashes();policy=json.loads((ROOT/POLICY).read_text(encoding='utf-8'))
    primaries=primary_hashes(policy);sources={**code_sources,**primaries}
    work.mkdir(parents=True);output.parent.mkdir(parents=True,exist_ok=True)
    for name in sources:
        target=work/'executed-sources'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    start=time.perf_counter();arrays={};jobs={};expected={};metrics={k:0. for k in (*policy['maximum'],*policy['minimum'])}
    metrics['sampled_current_shape_floor']=1.;metrics['sampled_differential_floor']=1.
    def guard():
        check_sources()
        if primary_hashes(policy)!=primaries:raise ValueError('Primary scientific artifacts changed during audit')
    def maximum(key,value):metrics[key]=max(metrics[key],float(value))
    def save(name,data):
        guard();p=work/(name+'.npz');np.savez(p,**data)
        arrays[name]=dict(path=p.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),shapes={k:list(np.asarray(v).shape) for k,v in data.items()})
        expected[name]={k:np.array(v,copy=True) for k,v in data.items()};guard()
    def run(name,initial,grid,function,method,tol,step):
        guard();tick=time.perf_counter();sol=solve_ivp(function,(0.,1.),initial,t_eval=grid[1:],dense_output=True,method=method,rtol=tol,atol=tol*policy['atol_over_rtol'],max_step=step)
        if not sol.success or not np.array_equal(sol.t,grid[1:]) or not np.all(np.isfinite(sol.y)):raise ValueError('Incomplete/nonfinite current radial IVP')
        states=np.vstack([initial.copy(),sol.y.T]);save(name,dict(radius_fraction=grid,initial=initial,states=states))
        jobs[name]=dict(method=method,rtol=tol,max_step=step,nfev=sol.nfev,seconds=time.perf_counter()-tick)
        return sol,states
    try:
        grid=np.linspace(0.,1.,policy['samples']);cases=[];q=reference.shape_matrix(policy);b=np.array(policy['shape_dipole'])
        m0=policy['gravitational_mass_kg'];r0=policy['areal_radius_m'];rho=3*m0/(4*np.pi*r0**3);omega=np.array(policy['angular_velocity_s_inv'])
        measure_keys=('mass_kg','areal_first_kg_m','harmonic_first_kg_m','areal_second_kg_m2','harmonic_second_kg_m2','axial_kg_m2_s','quadratic_kinetic_j')
        metric_keys=('mass_reference_relative','areal_first_reference_relative','harmonic_first_reference_relative','areal_second_reference_relative','harmonic_second_reference_relative','axial_reference_relative','kinetic_reference_relative')
        for index,c in enumerate(policy['compactnesses']):
            name='case-'+str(index)
            prod=run(name+'-production',np.array([1.,-0.]),grid,lambda s,z:harmonic.rhs(s,z,c),'DOP853',policy['production_rtol'],policy['production_max_radial_step'])
            refs=[run(name+'-reference-'+str(j),radial_reference.centre_state(c),grid,lambda s,z:radial_reference.riccati_rhs(s,z,c),'RK45',tol,policy['reference_max_radial_step']) for j,tol in enumerate(policy['reference_rtols'])]
            tight=run(name+'-tighter',radial_reference.centre_state(c),grid,lambda s,z:radial_reference.riccati_rhs(s,z,c),'DOP853',policy['tighter_rtol'],policy['tighter_max_radial_step'])
            chart=harmonic.match(prod[1][-1],c);order=policy['analytic_radial_orders'][1]
            analytic=reference.analytic_snapshot(c,refs[1][0],policy,order)
            coarse_analytic=reference.analytic_snapshot(c,refs[1][0],policy,policy['analytic_radial_orders'][0])
            loose=reference.analytic_snapshot(c,refs[0][0],policy,order);tighter=reference.analytic_snapshot(c,tight[0],policy,order)
            for key in measure_keys:
                maximum('analytic_quadrature_levels_relative',relative(coarse_analytic[key],analytic[key]))
                maximum('radial_reference_levels_relative',relative(loose[key],analytic[key]))
                maximum('radial_reference_tighter_relative',relative(tighter[key],analytic[key]))
            snapshots=[];points=[]
            for level,configuration in enumerate(policy['quadrature_levels']):
                radii,rweights=gauss_nodes(configuration['radial']);directions,aweights=reference.angular_grid(configuration['polar'],configuration['azimuthal'])
                count=len(directions);s=np.repeat(radii,count);unit=np.tile(directions,(len(radii),1));weight=np.repeat(rweights,count)*np.tile(aweights,len(radii))
                raw=prod[0].sol(s).T;geo=harmonic.interior_geometry(s,raw,chart)
                shape=1+np.einsum('ni,ij,nj->n',unit,q,unit)+unit@b
                coefficients=policy['radial_density_coefficients'];density=coefficients[0]+coefficients[1]*s*s
                metrics['sampled_current_shape_floor']=min(metrics['sampled_current_shape_floor'],float(np.min(shape*density)))
                metrics['sampled_differential_floor']=min(metrics['sampled_differential_floor'],float(np.min(geo['radius_derivative'])),float(np.min(geo['tangent_jacobian'])))
                x=r0*s[:,None]*unit;u=np.sqrt(1-2*c*s*s);lapse=(3*np.sqrt(1-2*c)-u)/2
                euclidean_volume=r0**3*s*s*weight;coordinate_density=rho*density*shape/u;masses=coordinate_density*euclidean_volume
                velocities=np.cross(omega,x)+policy['radial_rate_s_inv']*x
                projector=unit[:,:,None]*unit[:,None,:];areal_metric=np.eye(3)+(1/u**2-1)[:,None,None]*projector
                momenta=masses[:,None]*np.einsum('nij,nj->ni',areal_metric,velocities)/lapse[:,None]
                result=current.snapshot(masses,x,velocities,momenta,geo['radius_derivative'],geo['tangent_jacobian'],1/u**2,lapse)
                mapped_density=current.current_density_pullback(coordinate_density,result['determinants'])
                mapped_masses=mapped_density*result['determinants']*euclidean_volume
                maximum('density_measure_relative',relative(mapped_masses,masses))
                maximum('cotangent_pairing_relative',relative(result['mapped_pairing_kg_m2_s2'],result['areal_pairing_kg_m2_s2']))
                maximum('axial_pullback_relative',relative(result['mapped_axial_charge_kg_m2_s'],result['areal_axial_charge_kg_m2_s']))
                maximum('kinetic_pullback_relative',relative(result['mapped_quadratic_kinetic_j'],result['areal_quadratic_kinetic_j']))
                restored=result['jacobians'].transpose(0,2,1)@result['mapped_metrics']@result['jacobians']
                maximum('metric_pullback_relative',relative(restored,result['areal_metrics']))
                measures=dict(mass_kg=float(np.sum(masses)),areal_first_kg_m=result['areal_first_moment_kg_m'],harmonic_first_kg_m=result['mapped_first_moment_kg_m'],
                    areal_second_kg_m2=result['areal_second_moment_kg_m2'],harmonic_second_kg_m2=result['mapped_second_moment_kg_m2'],axial_kg_m2_s=result['areal_axial_charge_kg_m2_s'],quadratic_kinetic_j=result['areal_quadratic_kinetic_j'])
                for key,metric in zip(measure_keys,metric_keys):maximum(metric,relative(measures[key],analytic[key]))
                maximum('coordinate_C_M_reference_relative',max(relative(result['mapped_Euclidean_C_kg_m2'],analytic['harmonic_Euclidean_C_kg_m2']),relative(result['mapped_STF_M_kg_m2'],analytic['harmonic_STF_M_kg_m2'])))
                forward_p=np.einsum('nij,nj->ni',result['jacobians'],momenta)
                maximum('wrong_forward_momentum_pairing_relative',relative(np.sum(forward_p*result['mapped_velocities_m_s'],axis=1),result['areal_pairing_kg_m2_s2']))
                wrongaxial=np.sum(np.cross(result['mapped_positions_m'],masses[:,None]*result['mapped_velocities_m_s']),axis=0)
                maximum('wrong_Euclidean_momentum_axial_relative',relative(wrongaxial,result['areal_axial_charge_kg_m2_s']))
                wrongposition=np.einsum('nij,nj->ni',result['jacobians'],x);wrongsecond=wrongposition.T@(masses[:,None]*wrongposition)
                maximum('wrong_differential_as_position_relative',relative(wrongsecond,result['mapped_second_moment_kg_m2']))
                maximum('wrong_centre_affine_tensor_relative',relative(chart.scale**2*result['areal_second_moment_kg_m2'],result['mapped_second_moment_kg_m2']))
                wrongmass=float(np.dot(coordinate_density*result['determinants'],euclidean_volume))
                maximum('wrong_density_as_scalar_mass_relative',relative(wrongmass,measures['mass_kg']))
                save(name+'-pointgrid-'+str(level),dict(radius_fraction=s,directions=unit,quadrature_weights=weight,masses_kg=masses,positions_m=x,velocities_m_s=velocities,momenta_kg_m_s=momenta,
                    areal_coordinate_density=coordinate_density,mapped_coordinate_density=mapped_density,**result))
                snapshots.append(measures);points.append(len(s))
            for key in measure_keys:maximum('pointgrid_levels_relative',relative(snapshots[0][key],snapshots[1][key]))
            def serial(data):return {k:np.asarray(v).tolist() for k,v in data.items()}
            cases.append(dict(compactness=c,point_counts=points,chart=dict(scale=chart.scale,residual_gauge=chart.residual_gauge),analytic=serial(analytic),point_snapshots=[serial(x) for x in snapshots]))
            print(f'{name} C={c}: pointgrids{points} andanalytic tensor checks complete',flush=True)
        guard();copies_ok=all(hashlib.sha256((work/'executed-sources'/n).read_bytes()).hexdigest()==sha for n,sha in sources.items())
        verified=True;raw_ok=True;grid_ok=True
        for name,entry in arrays.items():
            p=ROOT/entry['path'];verified &= hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
            with np.load(p,allow_pickle=False) as saved:
                verified &= set(saved.files)==set(entry['shapes'])
                for k,shape in entry['shapes'].items():
                    verified &= list(saved[k].shape)==shape and np.all(np.isfinite(saved[k]))
                    verified &= np.array_equal(saved[k].view(np.uint64),expected[name][k].view(np.uint64))
                if name in jobs:
                    raw_ok &= np.array_equal(saved['states'][0].view(np.uint64),expected[name]['initial'].view(np.uint64))
                    grid_ok &= np.array_equal(saved['radius_fraction'].view(np.uint64),expected[name]['radius_fraction'].view(np.uint64))
        claims=('physical_lunar_mapping_certified','physical_accuracy_certified','PN_fluid_inertia_certified','temporal_E_J_conservation_certified','runtime_changed')
        flags=dict(sources_preserved=copies_ok,arrays_reverified=bool(verified),raw_initial_preserved=bool(raw_ok),grid_preserved=bool(grid_ok),physical_claims_false=all(policy[k] is False for k in claims))
        failed=failures(metrics,flags,policy)
        report=dict(changes=policy['changes'],policy=policy,sources=sources,arrays=arrays,jobs=jobs,metrics=metrics,confirmations=flags,cases=cases,passed=not failed,failed=failed,seconds=time.perf_counter()-start,
            **{k:False for k in claims},old_trajectories_reused=False,environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
            limitations='Supplied-current static-time tracer snapshot, not self-consistent rotating fluid or EOS. Coordinate D/C/STF moments are not physical PN fluid inertia. Quadratic particle kinetic measure omits full rest/potential/body-field energy; no temporal E/J conservation certified. DomainC>=1e-4 excludes Mooncompactness. No ADM/SSC/lunar map or tides. Sampled numerical agreement and reference sensitivity are not rigorous physical accuracy bounds.')
        text=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        with (work/'report.json').open('x',encoding='utf-8') as f:f.write(text)
        with output.open('x',encoding='utf-8') as f:f.write(text)
        if failed:raise ValueError('Predeclared criteria failed: '+', '.join(failed))
        return report
    except Exception as error:
        (work/'failure.json').write_text(json.dumps(dict(passed=False,error=repr(error),sources=sources,arrays=arrays,jobs=jobs,metrics=metrics),indent=2)+'\n',encoding='utf-8')
        raise


if __name__=='__main__':
    result=audit();print(json.dumps(dict(passed=result['passed'],metrics=result['metrics'],jobs=len(result['jobs']),arrays=len(result['arrays'])),indent=2))
