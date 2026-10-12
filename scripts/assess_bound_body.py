"""Fresh, source-frozen closed Newton bound-body model audit, stages 83-85."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT/'src'))
from scripts import bound_body as body
from scripts import independent_bound_reference as independent
from scripts.density_moments import density_pair
from scripts.assess_metric_spin import integrate_raw_initial, failures

POLICY = 'scripts/bound-body-policy.json'
USED_POLICIES = (POLICY, 'scripts/metric-spin-policy.json')


def source_hashes():
    paths = {p for folder in ('src', 'scripts', 'tests') for p in (ROOT/folder).rglob('*.py')}
    paths.update(ROOT/name for name in USED_POLICIES)
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


LOADED_SOURCES = source_hashes()


def check_sources():
    if source_hashes() != LOADED_SOURCES: raise ValueError('Scientific sources changed since module initialization')


def models(policy):
    m = policy['equilateral_mass_kg']; k = policy['equilateral_stiffness_N_m']
    length = np.sqrt(3)*policy['equilateral_rest_radius_m']; rc = policy['circular_radius_m']
    g = policy['gravitational_constant_m3_kg_s2']
    omega2 = g*m/(np.sqrt(3)*rc**3)+3*k/m*(1-length/(np.sqrt(3)*rc))
    kappa2 = 3*omega2-2*g*m/(np.sqrt(3)*rc**3)+3*k/m
    if omega2 <= 0 or kappa2 <= 0: raise ValueError('Stable circular test configuration required')
    omega = np.sqrt(omega2); ell = rc**2*omega
    duration = policy['rotation_periods']*2*np.pi/omega
    pars = body.Parameters((m,)*3, ((0,1,k,length),(0,2,k,length),(1,2,k,length)), g, policy['minimum_distance_m'])
    def equilateral(radius, radial_speed):
        z = np.array([[radius/policy['length_scale_m'], radial_speed/policy['velocity_scale_m_s'], 0.]])
        return independent.radial_cartesian(z,m,ell,policy['length_scale_m'],policy['velocity_scale_m_s'],policy['momentum_scale_kg_m_s'])[0]
    circle = equilateral(rc,0.); breathing = equilateral(policy['breathing_radius_m'],policy['breathing_radial_speed_m_s'])
    # Geometry is input, rest lengths are fixed from the initial shape before jobs.
    x = np.asarray(policy['asymmetric_positions_m']); masses = np.asarray(policy['asymmetric_masses_kg'])
    links = tuple((i,j,policy['asymmetric_link_base_N_m']+i+j,
                   policy['asymmetric_rest_fraction']*np.linalg.norm(x[j]-x[i]))
                  for i in range(len(masses)) for j in range(i+1,len(masses)))
    asymmetric = body.Parameters(tuple(masses),links,g,policy['minimum_distance_m'])
    v = np.cross(policy['asymmetric_omega_per_s'],x)+policy['asymmetric_expansion_per_s']*x+policy['asymmetric_velocity_offsets_m_s']
    raw = np.r_[x.ravel()/policy['length_scale_m'], (masses[:,None]*v).ravel()/policy['momentum_scale_kg_m_s']]
    return dict(circular=(pars,circle,duration),breathing=(pars,breathing,duration),
                asymmetric=(asymmetric,raw,policy['asymmetric_duration_s'])), dict(omega=omega,ell=ell,kappa2=kappa2,rest_length=length)


def physical(state, parameters, policy):
    n = len(parameters.masses)
    return state*np.r_[np.full(3*n,policy['length_scale_m']),np.full(3*n,policy['momentum_scale_kg_m_s'])]


def audit(*, work=None, output=None):
    work = Path(work or ROOT/'.tools/rotation85').resolve()
    output = Path(output or ROOT/'docs/bound-body-validation.json').resolve()
    if not work.is_relative_to(ROOT) or not output.is_relative_to(ROOT): raise ValueError('Outputs must be inside project')
    if work.exists() or output.exists(): raise FileExistsError('Fresh work/output paths required')
    check_sources(); sources = source_hashes(); policy = json.loads((ROOT/POLICY).read_text(encoding='utf-8'))
    cases, reduced = models(policy); work.mkdir(parents=True); output.parent.mkdir(parents=True,exist_ok=True)
    for name in sources:
        target = work/'executed-sources'/name; target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    arrays = {}; jobs = {}; expected_initial = {}; start = time.perf_counter()
    try:
        grid = np.linspace(0.,1.,policy['samples'])
        metrics = {key:0. for key in list(policy['maximum'])+list(policy['minimum'])}
        metrics['minimum_pair_distance_m'] = float('inf')
        solver_policy = dict(atol_over_rtol=policy['atol_over_rtol'],max_phase_step=policy['max_step_u'])
        def save(name,states,initial,duration,**extra):
            data = dict(u=grid,time_s=duration*grid,initial=initial,states=states,**extra)
            path = work/(name+'.npz'); np.savez(path,**data)
            arrays[name] = dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                               shapes={key:list(np.asarray(value).shape) for key,value in data.items()})
            expected_initial[name] = np.asarray(initial).copy()
        def run(name,initial,duration,function,method,tolerance):
            check_sources(); tick=time.perf_counter()
            states,nfev=integrate_raw_initial(function,initial,grid,method,tolerance,solver_policy)
            check_sources(); save(name,states,initial,duration)
            jobs[name]=dict(method=method,rtol=tolerance,atol=tolerance*policy['atol_over_rtol'],nfev=nfev,seconds=time.perf_counter()-tick)
            print(f'{name}: {nfev} evaluations, {jobs[name]["seconds"]:.2f}s',flush=True)
            return states
        def production_function(pars,duration):
            scale=physical(np.ones(6*len(pars.masses)),pars,policy)
            return lambda u,z: duration*body.rhs(u*duration,z*scale,pars)/scale
        trajectories={}
        for case,(pars,initial,duration) in cases.items():
            trajectories[case]=run(case+'-production',initial,duration,production_function(pars,duration),'DOP853',policy['production_rtol'])
        pars,initial,duration=cases['circular']
        radial_exact=np.c_[np.full(len(grid),policy['circular_radius_m']/policy['length_scale_m']),
                           np.zeros(len(grid)),reduced['omega']*duration*grid]
        circular_exact=independent.radial_cartesian(radial_exact,policy['equilateral_mass_kg'],reduced['ell'],policy['length_scale_m'],policy['velocity_scale_m_s'],policy['momentum_scale_kg_m_s'])
        save('circular-exact',circular_exact,circular_exact[0],duration)
        def position_error(a,b,n):return float(np.max(np.linalg.norm((a[:,:3*n]-b[:,:3*n]).reshape(-1,n,3),axis=2)))
        def momentum_error(a,b,n):return float(np.max(np.linalg.norm((a[:,3*n:]-b[:,3*n:]).reshape(-1,n,3),axis=2)))
        metrics['circular_position_scaled']=position_error(trajectories['circular'],circular_exact,3)
        metrics['circular_momentum_scaled']=momentum_error(trajectories['circular'],circular_exact,3)
        # Reduced states have their own raw epoch0, not copied from Cartesian ODE.
        pars,initial,duration=cases['breathing']
        radial_initial=np.array([policy['breathing_radius_m']/policy['length_scale_m'],policy['breathing_radial_speed_m_s']/policy['velocity_scale_m_s'],0.])
        radial_function=lambda u,z: independent.radial_rhs(u,z,policy['equilateral_mass_kg'],policy['equilateral_stiffness_N_m'],reduced['rest_length'],policy['gravitational_constant_m3_kg_s2'],reduced['ell'],duration,policy['length_scale_m'],policy['velocity_scale_m_s'])
        refs=[run('breathing-reduced-'+str(i),radial_initial,duration,radial_function,'RK45',tol) for i,tol in enumerate(policy['reference_rtols'])]
        tight=run('breathing-reduced-dop853',radial_initial,duration,radial_function,'DOP853',policy['tighter_rtol'])
        def reconstruct(z):return independent.radial_cartesian(z,policy['equilateral_mass_kg'],reduced['ell'],policy['length_scale_m'],policy['velocity_scale_m_s'],policy['momentum_scale_kg_m_s'])
        cart=[reconstruct(z) for z in refs]; tightcart=reconstruct(tight)
        metrics['breathing_reduced_position_scaled']=position_error(trajectories['breathing'],cart[1],3)
        metrics['breathing_reduced_momentum_scaled']=momentum_error(trajectories['breathing'],cart[1],3)
        metrics['reduced_levels_scaled']=max(position_error(cart[0],cart[1],3),momentum_error(cart[0],cart[1],3))
        metrics['reduced_tighter_scaled']=max(position_error(cart[1],tightcart,3),momentum_error(cart[1],tightcart,3))
        def cartesian_function(pars,duration):
            return lambda u,z: independent.cartesian_rhs(u,z,pars.masses,pars.links,pars.gravitational_constant,duration,policy['length_scale_m'],policy['momentum_scale_kg_m_s'])
        check=run('breathing-cartesian',initial,duration,cartesian_function(pars,duration),'RK45',policy['reference_rtols'][1])
        metrics['breathing_cartesian_position_scaled']=position_error(trajectories['breathing'],check,3)
        metrics['breathing_cartesian_momentum_scaled']=momentum_error(trajectories['breathing'],check,3)
        pars,initial,duration=cases['asymmetric']
        asym=[run('asymmetric-reference-'+str(i),initial,duration,cartesian_function(pars,duration),'RK45',tol) for i,tol in enumerate(policy['reference_rtols'])]
        metrics['asymmetric_position_scaled']=position_error(trajectories['asymmetric'],asym[1],4)
        metrics['asymmetric_momentum_scaled']=momentum_error(trajectories['asymmetric'],asym[1],4)
        metrics['asymmetric_levels_scaled']=max(position_error(asym[0],asym[1],4),momentum_error(asym[0],asym[1],4))
        diagnostics={}
        def maximize(key,value):metrics[key]=max(metrics[key],float(value))
        for case,(pars,initial,duration) in cases.items():
            first=body.rotation_split(physical(initial,pars,policy),pars); records=[]
            for u,z in zip(grid,trajectories[case]):
                y=physical(z,pars,policy); out=body.rotation_split(y,pars)
                d=out['second_moment']; c=out['inertia']; w=out['omega']
                x,p,m=body.unpack(y,pars)
                distances=[np.linalg.norm(x[j]-x[i]) for i in range(len(m)) for j in range(i+1,len(m))]
                metrics['minimum_pair_distance_m']=min(metrics['minimum_pair_distance_m'],float(min(distances)))
                maximize('pair_reaction_scaled',np.linalg.norm(np.sum(out['force'],axis=0))/policy['force_scale_N'])
                maximize('total_torque_scaled',np.linalg.norm(np.sum(np.cross(x,out['force']),axis=0))/(policy['force_scale_N']*policy['length_scale_m']))
                maximize('tensor_virial_scaled',np.linalg.norm(.5*out['second_moment_ddot']-out['kinetic_tensor']-out['pair_virial'])/policy['energy_scale_joule'])
                maximize('density_compatibility_relative',np.linalg.norm(density_pair(c,out['multipole'])-d)/np.linalg.norm(d))
                maximize('residual_spin_scaled',np.linalg.norm(out['residual_spin'])/policy['angular_scale_kg_m2_s'])
                maximize('kinetic_split_scaled',abs(out['internal_kinetic']-out['rotation_energy']-out['residual_energy'])/policy['energy_scale_joule'])
                maximize('energy_drift_scaled',abs(out['energy']-first['energy'])/policy['energy_scale_joule'])
                maximize('angular_drift_scaled',np.linalg.norm(out['angular']-first['angular'])/policy['angular_scale_kg_m2_s'])
                maximize('momentum_drift_scaled',np.linalg.norm(out['momentum']-first['momentum'])/policy['momentum_scale_kg_m_s'])
                maximize('com_linear_scaled',np.linalg.norm(out['centre']-first['centre']-first['centre_velocity']*u*duration)/policy['length_scale_m'])
                records.append([out['energy'],*out['angular'],*out['momentum'],out['internal_kinetic'],out['elastic'],out['gravity'],out['rotation_energy'],out['residual_energy'],*w])
                if case=='breathing':
                    hat=np.array([[0.,-w[2],w[1]],[w[2],0.,-w[0]],[-w[1],w[0],0.]])
                    maximize('wrong_rigid_inertia_rate_scaled',np.linalg.norm(out['inertia_dot']-hat@c+c@hat)/policy['inertia_rate_scale_kg_m2_s'])
                    maximize('frozen_inertia_spin_scaled',np.linalg.norm(first['inertia']@w-out['spin'])/policy['angular_scale_kg_m2_s'])
                    maximize('deformation_kinetic_fraction',out['residual_energy']/out['internal_kinetic'])
                    maximize('kinetic_only_drift_scaled',abs(out['kinetic']-first['kinetic'])/policy['energy_scale_joule'])
                    maximize('spring_energy_as_virial_scaled',abs(np.trace(out['pair_virial'])-out['gravity']-out['elastic'])/policy['energy_scale_joule'])
            diagnostics[case]=np.asarray(records).tolist()
            # Independent force gradients evaluated at several later epochs too.
            for index in (0,len(grid)//3,2*len(grid)//3,len(grid)-1):
                y=physical(trajectories[case][index],pars,policy)
                force=body.diagnostics(y,pars)['force']; grad=independent.gradient(y,pars.masses,pars.links,pars.gravitational_constant)
                maximize('force_gradient_scaled',np.linalg.norm(force.ravel()+grad[:3*len(pars.masses)])/policy['force_scale_N'])
        radii=np.linalg.norm(trajectories['breathing'][:,:9].reshape(-1,3,3),axis=2)
        metrics['breathing_radius_span_scaled']=float(np.max(radii)-np.min(radii))
        pars,initial,duration=cases['circular'];x,p,m=body.unpack(physical(initial,pars,policy),pars)
        no_links=body.Parameters(pars.masses,(),pars.gravitational_constant,pars.minimum_distance)
        full_force=body.fields(x,pars)[0]; gravitational_force=body.fields(x,no_links)[0]
        metrics['omitted_binding_force_scaled']=float(np.linalg.norm(full_force-gravitational_force)/policy['force_scale_N'])
        # Omit the partner reaction for one actual link, retaining all other forces.
        i,j,k,length=pars.links[0];q=x[j]-x[i];distance=np.linalg.norm(q)
        pair=(pars.gravitational_constant*m[i]*m[j]/distance**2+k*(distance-length))*q/distance
        metrics['omitted_pair_reaction_scaled']=float(np.linalg.norm(pair)/policy['force_scale_N'])
        source_copy_ok=all(hashlib.sha256((work/'executed-sources'/name).read_bytes()).hexdigest()==sha for name,sha in sources.items())
        verified=True;raw_ok=True;grid_ok=True
        for name,entry in arrays.items():
            path=ROOT/entry['path'];verified &= hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
            with np.load(path,allow_pickle=False) as saved:
                for key,shape in entry['shapes'].items():verified &= list(saved[key].shape)==shape and np.all(np.isfinite(saved[key]))
                raw_ok &= np.array_equal(saved['initial'].view(np.uint64),expected_initial[name].view(np.uint64))
                raw_ok &= np.array_equal(saved['states'][0].view(np.uint64),expected_initial[name].view(np.uint64))
                grid_ok &= np.array_equal(saved['u'].view(np.uint64),grid.view(np.uint64))
                if name.startswith('asymmetric'):duration=cases['asymmetric'][2]
                else:duration=cases['circular'][2]
                grid_ok &= np.array_equal(saved['time_s'].view(np.uint64),(duration*grid).view(np.uint64))
        confirmations=dict(sources_preserved=source_hashes()==sources and source_copy_ok,arrays_reverified=bool(verified),
            raw_initial_preserved=bool(raw_ok),grid_preserved=bool(grid_ok),physical_claims_false=bool(policy['physical_lunar_mapping_certified'] is False and policy['physical_accuracy_certified'] is False))
        failed=failures(metrics,confirmations,policy)
        report=dict(changes=policy['changes'],policy=policy,sources=sources,arrays=arrays,jobs=jobs,metrics=metrics,confirmations=confirmations,
            models={case:dict(masses=pars.masses,links=pars.links,g=pars.gravitational_constant,minimum_distance=pars.minimum_distance,initial=initial.tolist(),duration_s=duration) for case,(pars,initial,duration) in cases.items()},
            reduced_parameters=reduced,diagnostics_columns=['energy','Jx','Jy','Jz','Px','Py','Pz','Kint','elastic','gravity','Krotation','Kresidual','omega_x','omega_y','omega_z'],diagnostics=diagnostics,
            passed=not failed,failed=failed,seconds=time.perf_counter()-start,environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
            physical_lunar_mapping_certified=False,physical_accuracy_certified=False,pn_inertia_implemented=False,runtime_changed=False,old_trajectories_reused=False,
            limitations='Newton finite-point elastic network, synthetic G, instantaneous central links, no continuum stress/PN field energy/SSC/time-scale mapping/physical lunar material. Fixed-epoch reference sensitivity is not a rigorous error bound.')
        text=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        with (work/'report.json').open('x',encoding='utf-8') as f:f.write(text)
        with output.open('x',encoding='utf-8') as f:f.write(text)
        if failed:raise ValueError('Predeclared criteria failed: '+', '.join(failed))
        return report
    except Exception as error:
        (work/'failure.json').write_text(json.dumps(dict(passed=False,error=repr(error),sources=sources,arrays=arrays,jobs=jobs,metrics=locals().get('metrics',{})),indent=2)+'\n',encoding='utf-8')
        raise


if __name__=='__main__':
    result=audit()
    print(json.dumps(dict(passed=result['passed'],metrics=result['metrics']),indent=2))
