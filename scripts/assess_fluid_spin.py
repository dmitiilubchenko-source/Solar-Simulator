"""Fresh source-frozen constant-energy-density continuum-spin radial audit."""
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np
import scipy
from scipy.integrate import simpson

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'src'))
from scripts import continuum_sphere as continuum
from scripts import fluid_spin as spin
from scripts import independent_fluid_reference as reference
from scripts.assess_metric_spin import integrate_raw_initial,failures

POLICY='scripts/fluid-spin-policy.json'
USED_POLICIES=(POLICY,'scripts/metric-spin-policy.json')
PRIMARY_ARTIFACTS=('.tools/rotation86-89/hartle1967.pdf','.tools/rotation86-89/source-review.json')


def source_hashes():
    paths={p for folder in ('src','scripts','tests') for p in (ROOT/folder).rglob('*.py')}
    paths.update(ROOT/name for name in USED_POLICIES)
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


LOADED_SOURCES=source_hashes()


def check_sources():
    if source_hashes()!=LOADED_SOURCES:raise ValueError('Scientific sources changed since module initialization')


def primary_hashes():
    """Private research cache is required for fresh audit, never for import."""
    result={}
    for name in PRIMARY_ARTIFACTS:
        path=ROOT/name
        if not path.is_file():raise FileNotFoundError('Primary scientific artifact unavailable: '+name)
        result[name]=hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def check_primary_sources(expected):
    if primary_hashes()!=expected:raise ValueError('Primary scientific artifacts changed during audit')


def audit(*,work=None,output=None):
    work=Path(work or ROOT/'.tools/rotation90').resolve();output=Path(output or ROOT/'docs/continuum-spin-validation-r2.json').resolve()
    if not work.is_relative_to(ROOT) or not output.is_relative_to(ROOT):raise ValueError('Outputs must be inside project')
    if work.exists() or output.exists():raise FileExistsError('Fresh work/output paths required')
    check_sources();code_sources=source_hashes();primary_sources=primary_hashes()
    sources={**code_sources,**primary_sources};policy=json.loads((ROOT/POLICY).read_text(encoding='utf-8'))
    work.mkdir(parents=True);output.parent.mkdir(parents=True,exist_ok=True)
    for name in sources:
        target=work/'executed-sources'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    start=time.perf_counter();arrays={};jobs={};expected={}
    try:
        grid=np.linspace(0.,1.,policy['samples']);metrics={key:0. for key in (*policy['maximum'],*policy['minimum'])}
        solver=dict(atol_over_rtol=policy['atol_over_rtol'],max_phase_step=policy['max_radial_step'])
        def maximum(key,value):metrics[key]=max(metrics[key],float(value))
        def run(name,initial,nodes,function,method,tolerance):
            check_sources();check_primary_sources(primary_sources);tick=time.perf_counter()
            states,nfev=integrate_raw_initial(function,initial,nodes,method,tolerance,solver)
            check_sources();check_primary_sources(primary_sources);path=work/(name+'.npz');data=dict(radius_fraction=nodes,initial=initial,states=states)
            np.savez(path,**data);arrays[name]=dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                shapes={key:list(np.asarray(value).shape) for key,value in data.items()})
            expected[name]=(initial.copy(),nodes.copy());jobs[name]=dict(method=method,rtol=tolerance,atol=tolerance*policy['atol_over_rtol'],nfev=nfev,seconds=time.perf_counter()-tick)
            print(f'{name}: {nfev} evaluations, {jobs[name]["seconds"]:.2f}s',flush=True)
            return states
        results=[]
        for index,c in enumerate(policy['compactnesses']):
            name='case-'+str(index);bg=continuum.background(grid,c);p=bg['pressure_ratio']
            maximum('metric_stress_logj_scaled',np.max(abs(bg['logarithmic_j_rate']-reference.stress_logj_rate(grid,c)))/c)
            tov=-c*grid*(1+p)*(1+3*p)/(1-2*c*grid**2)
            maximum('tov_residual_scaled',np.max(abs(bg['pressure_ratio_rate']-tov))/c)
            maximum('surface_metric_matching',max(abs(bg['lapse'][-1]-np.sqrt(1-2*c)),abs(bg['j'][-1]-1.),abs(p[-1])))
            initial=np.array([1.,0.])
            prod=run(name+'-production',initial,grid,lambda s,z:spin.rhs(s,z,c),'DOP853',policy['production_rtol'])
            refs=[run(name+'-reference-'+str(i),np.array([0.]),grid,lambda s,z:reference.riccati_rhs(s,z,c),'RK45',tol) for i,tol in enumerate(policy['reference_rtols'])]
            tight=run(name+'-reference-dop853',np.array([0.]),grid,lambda s,z:reference.riccati_rhs(s,z,c),'DOP853',policy['tighter_rtol'])
            wrong=run(name+'-no-pressure',np.array([0.]),grid,lambda s,z:reference.riccati_rhs(s,z,c,omit_pressure=True),'DOP853',policy['production_rtol'])
            boundary=spin.boundary(prod[-1],c);a=boundary['inertia_factor'];norm=boundary['omega_over_central']
            zprod=grid*prod[:,1]/prod[:,0];arefs=[float(reference.riccati_inertia(z[-1,0],c)) for z in refs]
            atight=float(reference.riccati_inertia(tight[-1,0],c));awrong=float(reference.riccati_inertia(wrong[-1,0],c))
            maximum('reference_profile_z_absolute',np.max(abs(zprod-refs[1][:,0])))
            maximum('reference_inertia_absolute',abs(a-arefs[1]))
            maximum('reference_levels_inertia_absolute',abs(arefs[0]-arefs[1]))
            maximum('reference_tighter_inertia_absolute',abs(arefs[1]-atight))
            ext,deriv=spin.exterior(1.,a,c)
            maximum('exterior_value_matching',abs(ext-boundary['normalized_surface']))
            maximum('exterior_derivative_matching',abs(deriv-boundary['normalized_surface_derivative']))
            integrand=reference.inertia_integrand(grid,c,prod[:,0]/norm)
            integral=float(simpson(integrand,x=grid));coarse=float(simpson(integrand[::2],x=grid[::2]))
            maximum('matter_integral_inertia_absolute',abs(integral-a))
            maximum('matter_integral_levels_absolute',abs(integral-coarse))
            sphere=continuum.Sphere(policy['gravitational_mass_kg'],policy['areal_radius_m'],policy['gravitational_constant'],
                np.sqrt(policy['gravitational_constant']*policy['gravitational_mass_kg']/policy['areal_radius_m']/c))
            totals=continuum.newton_integrals(sphere)
            maximum('newton_pressure_virial_relative',abs(totals['gravitational_energy']+3*totals['pressure_volume_integral'])/abs(totals['gravitational_energy']))
            charges=spin.charges(prod[-1],sphere,policy['angular_velocity_s_inv'])
            expected_j=a*sphere.gravitational_mass_kg*sphere.areal_radius_m**2*policy['angular_velocity_s_inv']
            maximum('SI_charge_scaling_relative',abs(charges['angular_kg_m2_s']-expected_j)/abs(expected_j))
            maximum('omitted_pressure_inertia_absolute',abs(a-awrong))
            maximum('constant_newton_inertia_absolute',abs(a-.4))
            maximum('omitted_boundary_frequency_absolute',abs(prod[-1,1]/(6*c)-a))
            maximum('ignored_frame_drag_profile_absolute',np.max(abs(prod[:,0]/norm-1.)))
            results.append(dict(compactness=c,inertia_factor=a,reference_inertias=arefs,tighter_inertia=atight,no_pressure_inertia=awrong,
                integral_inertia=integral,coarse_integral_inertia=coarse,boundary=boundary,SI=dict(mass_kg=sphere.gravitational_mass_kg,radius_m=sphere.areal_radius_m,
                    G=sphere.gravitational_constant,c=sphere.light_speed_m_s,energy_density_mass_kg_m3=sphere.energy_density_mass,**charges)))
        selected=[results[i] for i in policy['order_cases']];cs=np.array([x['compactness'] for x in selected]);actual=np.array([x['inertia_factor'] for x in selected])
        first=actual-reference.inertia_series(cs,1);second=actual-reference.inertia_series(cs,2)
        first_ratios=first[:-1]/first[1:];second_ratios=second[:-1]/second[1:]
        metrics['first_PN_c4_ratio_deviation']=float(np.max(abs(first_ratios-16.)))
        metrics['second_order_c6_ratio_deviation']=float(np.max(abs(second_ratios-64.)))
        slopes=(actual-.4)/cs
        richardson=(4*slopes[1]-slopes[0])/3
        metrics['first_PN_slope_Richardson_absolute']=float(abs(richardson-12/35))
        metrics['newton_small_C_inertia_absolute']=float(abs(actual[-1]-.4))
        metrics['published_second_coefficient_absolute']=float(abs(first[-1]/cs[-1]**2-212/525))
        wrong_slope=(selected[-1]['no_pressure_inertia']-.4)/cs[-1]
        metrics['no_pressure_slope_absolute']=float(abs(wrong_slope-2/7))
        c=policy['compactnesses'][policy['tov_case']];inward=grid[::-1].copy()
        tov_states=[run('tov-reference-'+str(i),np.array([0.]),inward,lambda s,z:reference.tov_rhs(s,z,c),'RK45',tol) for i,tol in enumerate(policy['reference_rtols'])]
        metrics['tov_reference_pressure_absolute']=float(np.max(abs(tov_states[1][:,0]-continuum.background(inward,c)['pressure_ratio'])))
        metrics['tov_levels_pressure_absolute']=float(np.max(abs(tov_states[0]-tov_states[1])))
        copy_ok=all(hashlib.sha256((work/'executed-sources'/name).read_bytes()).hexdigest()==sha for name,sha in sources.items())
        verified=True;raw_ok=True;grid_ok=True
        for name,entry in arrays.items():
            path=ROOT/entry['path'];verified &= hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
            with np.load(path,allow_pickle=False) as saved:
                for key,shape in entry['shapes'].items():verified &= list(saved[key].shape)==shape and np.all(np.isfinite(saved[key]))
                initial,nodes=expected[name]
                raw_ok &= np.array_equal(saved['initial'].view(np.uint64),initial.view(np.uint64))
                raw_ok &= np.array_equal(saved['states'][0].view(np.uint64),initial.view(np.uint64))
                grid_ok &= np.array_equal(saved['radius_fraction'].view(np.uint64),nodes.view(np.uint64))
        confirmations=dict(sources_preserved=source_hashes()==code_sources and primary_hashes()==primary_sources and copy_ok,arrays_reverified=bool(verified),raw_initial_preserved=bool(raw_ok),
            grid_preserved=bool(grid_ok),physical_claims_false=bool(policy['physical_lunar_mapping_certified'] is False and policy['physical_accuracy_certified'] is False))
        failed=failures(metrics,confirmations,policy)
        report=dict(changes=policy['changes'],refinement_change=90,policy=policy,sources=sources,arrays=arrays,jobs=jobs,metrics=metrics,confirmations=confirmations,
            cases=results,order=dict(compactnesses=cs.tolist(),first_PN_remainders=first.tolist(),second_order_remainders=second.tolist(),
                first_PN_c4_ratios=first_ratios.tolist(),second_order_c6_ratios=second_ratios.tolist(),first_PN_Richardson_slope=float(richardson),no_pressure_slope=float(wrong_slope)),
            passed=not failed,failed=failed,seconds=time.perf_counter()-start,environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
            physical_lunar_mapping_certified=False,physical_accuracy_certified=False,finite_rotation_energy_implemented=False,runtime_changed=False,old_trajectories_reused=False,
            limitations='Constant energy density incompressible acausal benchmark, linear-Omega only. Gravitational mass/areal radius/asymptotic time, not baryon mass/harmonic or ADM lunar tensors. No finite-Omega^2 shape/mass/energy correction, tides, temporal orbit-spin dynamics, or physical Moon calibration. Sampled radial checks and reference sensitivity are not rigorous error bounds.')
        text=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        with (work/'report.json').open('x',encoding='utf-8') as f:f.write(text)
        with output.open('x',encoding='utf-8') as f:f.write(text)
        if failed:raise ValueError('Predeclared criteria failed: '+', '.join(failed))
        return report
    except Exception as error:
        (work/'failure.json').write_text(json.dumps(dict(passed=False,error=repr(error),sources=sources,arrays=arrays,jobs=jobs,metrics=locals().get('metrics',{})),indent=2)+'\n',encoding='utf-8')
        raise


if __name__=='__main__':
    result=audit();print(json.dumps(dict(passed=result['passed'],metrics=result['metrics'],order=result['order']),indent=2))
