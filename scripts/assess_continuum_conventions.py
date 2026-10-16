"""Fresh, source-frozen spherical mass/chart/observer qualification audit."""
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
from scripts import continuum_conventions as convention
from scripts import fluid_spin as spin
from scripts import independent_fluid_reference as fluid_reference
from scripts import independent_conventions_reference as reference
from scripts.continuum_sphere import Sphere
from scripts.assess_metric_spin import integrate_raw_initial, failures

POLICY='scripts/continuum-conventions-policy.json'
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
        path=ROOT/name
        if not path.is_file():raise FileNotFoundError('Primary scientific artifact unavailable: '+name)
        actual=hashlib.sha256(path.read_bytes()).hexdigest()
        if actual!=expected:raise ValueError('Pinned primary scientific artifact changed: '+name)
        result[name]=actual
    return result


def audit(*,work=None,output=None):
    work=Path(work or ROOT/'.tools/rotation95').resolve()
    output=Path(output or ROOT/'docs/continuum-conventions-validation.json').resolve()
    if not work.is_relative_to(ROOT) or not output.is_relative_to(ROOT):raise ValueError('Outputs must be inside project')
    if work.exists() or output.exists():raise FileExistsError('Fresh work/output paths required')
    check_sources();code_sources=source_hashes();policy=json.loads((ROOT/POLICY).read_text(encoding='utf-8'))
    primaries=primary_hashes(policy);sources={**code_sources,**primaries}
    work.mkdir(parents=True);output.parent.mkdir(parents=True,exist_ok=True)
    for name in sources:
        target=work/'executed-sources'/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((ROOT/name).read_bytes())
    start=time.perf_counter();arrays={};jobs={};expected={}
    metrics={key:0. for key in (*policy['maximum'],*policy['minimum'])}
    def guard():
        check_sources()
        if primary_hashes(policy)!=primaries:raise ValueError('Primary scientific artifacts changed during audit')
    def maximum(key,value):metrics[key]=max(metrics[key],float(value))
    def save(name,data):
        guard();path=work/(name+'.npz');np.savez(path,**data)
        arrays[name]=dict(path=path.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                          shapes={k:list(np.asarray(v).shape) for k,v in data.items()})
        expected[name]={k:np.array(v,copy=True) for k,v in data.items()};guard()
    def run_spin(name,initial,nodes,function):
        guard();tick=time.perf_counter()
        states,nfev=integrate_raw_initial(function,initial,nodes,'DOP853',policy['production_rtol'],
            dict(atol_over_rtol=policy['atol_over_rtol'],max_phase_step=policy['spin_max_radial_step']))
        guard();save(name,dict(radius_fraction=nodes,initial=initial,states=states))
        jobs[name]=dict(method='DOP853',rtol=policy['production_rtol'],nfev=nfev,seconds=time.perf_counter()-tick)
        return states
    def run_log(name,c,nodes,method,tolerance,max_step):
        guard();tick=time.perf_counter();initial=np.array([np.log(reference.surface_isotropic_fraction(c))])
        solution=solve_ivp(lambda s,z:reference.log_radius_rhs(s,z,c),(1.,0.),initial,t_eval=nodes[1:],
            dense_output=True,method=method,rtol=tolerance,atol=tolerance*policy['atol_over_rtol'],max_step=max_step)
        if not solution.success or not np.array_equal(solution.t,nodes[1:]) or not np.all(np.isfinite(solution.y)):
            raise ValueError('Incomplete/nonfinite independent log-radius integration')
        states=np.vstack([initial.copy(),solution.y.T]);guard()
        save(name,dict(radius_fraction=nodes,initial=initial,states=states))
        jobs[name]=dict(method=method,rtol=tolerance,atol=tolerance*policy['atol_over_rtol'],max_step=max_step,
                        nfev=solution.nfev,seconds=time.perf_counter()-tick)
        return solution,states
    try:
        grid=np.linspace(0.,1.,policy['samples']);inward=grid[::-1].copy();results=[]
        for i,c in enumerate(policy['compactnesses']):
            name='case-'+str(i);geo=convention.isotropic_geometry(grid,c);x=geo['isotropic_radius_fraction']
            q=float(convention.proper_volume_fraction(1.,c));qs=[reference.proper_mass_ratio(c,n) for n in policy['quadrature_orders']]
            maximum('proper_mass_quadrature_absolute',abs(q-qs[1]));maximum('proper_mass_quadrature_levels_absolute',abs(qs[0]-qs[1]))
            logs=[run_log(name+'-log-'+str(j),c,inward,'RK45',tol,policy['log_max_radial_step']) for j,tol in enumerate(policy['log_reference_rtols'])]
            tight=run_log(name+'-log-tighter',c,inward,'DOP853',policy['tighter_rtol'],policy['tighter_max_radial_step'])
            production_ratio=1/geo['conformal_squared'];ref_ratios=[np.exp(z[1][::-1,0]) for z in logs]
            tighter_ratio=np.exp(tight[1][::-1,0])
            maximum('log_radius_profile_absolute',np.max(abs(production_ratio-ref_ratios[1])))
            maximum('log_radius_levels_absolute',np.max(abs(ref_ratios[0]-ref_ratios[1])))
            maximum('log_radius_tighter_absolute',np.max(abs(ref_ratios[1]-tighter_ratio)))
            maximum('metric_pullback_absolute',np.max(abs(geo['radius_derivative']/production_ratio-geo['areal_volume_weight'])))
            maximum('metric_pullback_absolute',np.max(abs(geo['isotropic_volume_weight']*x*x*geo['radius_derivative']-grid*grid*geo['areal_volume_weight'])))
            xs=float(geo['surface_isotropic_fraction']);maximum('surface_exterior_matching_absolute',abs(xs*(1+c/(2*xs))**2-1))
            sphere=Sphere(policy['gravitational_mass_kg'],policy['areal_radius_m'],policy['gravitational_constant'],
                np.sqrt(policy['gravitational_constant']*policy['gravitational_mass_kg']/policy['areal_radius_m']/c))
            tracers={"constant0.7":lambda s:np.full_like(s,.7),"quadratic0.4+0.2s2":lambda s:.4+.2*s*s}
            masses={}
            for tracer_name in policy['baryon_tracers']:
                density=tracers[tracer_name];areals=[];isos=[];data={}
                for n in policy['quadrature_orders']:
                    nodes,weights=reference.gauss_nodes(n)
                    measures=convention.mass_integrands(nodes,sphere,sphere.energy_density_mass*density(nodes))
                    production=float(np.dot(weights,measures['baryon_mass_rate_kg'])/sphere.gravitational_mass_kg)
                    areal=reference.baryon_areal_ratio(c,density,n)
                    iso,snodes,xnodes=reference.baryon_isotropic_ratio(c,density,logs[1][0],n)
                    maximum('baryon_coordinate_integrals_absolute',max(abs(production-iso),abs(production-areal)))
                    maximum('isotropic_inverse_absolute',np.max(abs(convention.areal_from_isotropic(xnodes,c)-snodes)))
                    areals.append(areal);isos.append(iso)
                    data.update({f'areal_nodes_{n}':nodes,f'isotropic_nodes_{n}':xnodes,f'inverted_areal_nodes_{n}':snodes,
                                 f'areal_weights_{n}':weights,f'mass_measures_{n}':np.stack(list(measures.values()),axis=1)})
                coarse=reference.baryon_isotropic_ratio(c,density,logs[0][0],policy['quadrature_orders'][1])[0]
                fine=reference.baryon_isotropic_ratio(c,density,tight[0],policy['quadrature_orders'][1])[0]
                maximum('baryon_coordinate_reference_sensitivity_absolute',max(abs(isos[1]-coarse),abs(isos[1]-fine)))
                maximum('baryon_quadrature_levels_absolute',max(abs(isos[0]-isos[1]),abs(areals[0]-areals[1])))
                masses[tracer_name]=dict(areal=areals,isotropic=isos,log_coarse=coarse,log_tighter=fine)
                save(name+'-baryon-'+tracer_name.replace('+','-'),data)
            prod=run_spin(name+'-spin',np.array([1.,0.]),grid,lambda s,z:spin.rhs(s,z,c))
            riccati=run_spin(name+'-spin-reference',np.array([0.]),grid,lambda s,z:fluid_reference.riccati_rhs(s,z,c))
            matched=spin.boundary(prod[-1],c);a=matched['inertia_factor'];h=prod[:,0]/matched['omega_over_central']
            maximum('spin_reference_inertia_absolute',abs(a-fluid_reference.riccati_inertia(riccati[-1,0],c)))
            w=policy['angular_velocity_s_inv'];rates=convention.observer_rates(grid,h,sphere,w,surface_state=prod[-1])
            # Lapse from independent analytic metric; coframe projection includes shift.
            lapse=(3*np.sqrt(1-2*c)-np.sqrt(1-2*c*grid*grid))/2
            projected=np.array([reference.tetrad_rates(sphere.areal_radius_m*s,n,w*(1-hj),w) for s,n,hj in zip(grid,lapse,h)])
            scale=sphere.areal_radius_m*abs(w)
            maximum('tetrad_clock_speed_relative',max(np.max(abs(projected[:,0]-1)),
                np.max(abs(projected[:,1]-rates['equatorial_zamo_speed_m_s']))/scale,
                np.max(abs(w/lapse-rates['static_rate_s_inv']))/abs(w)))
            angular=rates['exterior_angular_momentum_kg_m2_s']
            maximum('local_response_J_relative',max(np.max(abs(rates['apparent_static_response_kg_m2']*rates['static_rate_s_inv']-angular)),
                np.max(abs(rates['apparent_zamo_response_kg_m2']*rates['zamo_relative_rate_s_inv']-angular)))/abs(angular))
            responses=convention.surface_responses(prod[-1],c)
            maximum('wrong_Euclidean_volume_absolute',abs(q-1))
            maximum('wrong_areal_as_isotropic_absolute',abs(xs-1))
            maximum('wrong_coordinate_density_as_scalar_absolute',np.max(abs(geo['isotropic_volume_weight']-geo['areal_volume_weight'])))
            maximum('wrong_no_lapse_relative',np.max(abs(w-rates['static_rate_s_inv']))/abs(w))
            maximum('wrong_no_shift_relative',np.max(abs(w/lapse-rates['zamo_relative_rate_s_inv']))/abs(w))
            save(name+'-geometry-observers',dict(radius_fraction=grid,isotropic_fraction=x,geometry=np.stack([geo[k] for k in ('radius_derivative','conformal_squared','isotropic_volume_weight','areal_volume_weight')],axis=1),
                normalized_baromega=h,observer_rates=np.stack([rates[k] for k in ('static_rate_s_inv','zamo_relative_rate_s_inv','dragging_rate_s_inv','equatorial_zamo_speed_m_s')],axis=1),reference_tetrad=projected))
            results.append(dict(compactness=c,proper_energy_mass_ratio=q,proper_mass_quadratures=qs,surface_isotropic_fraction=xs,
                baryon_tracers=masses,inertia_factor=a,responses=responses,SI=dict(mass_kg=sphere.gravitational_mass_kg,areal_radius_m=sphere.areal_radius_m,
                G=sphere.gravitational_constant,c=sphere.light_speed_m_s,omega=w,angular_momentum=angular)))
            print(f'{name} C={c}: mass/chart/observer jobs complete',flush=True)
        selected=[results[i] for i in policy['order_cases']];cs=np.array([x['compactness'] for x in selected]);order={}
        series=reference.response_linear_series(cs)
        for key in series:
            values=np.array([x['responses'][key] for x in selected]);remainder=values-series[key];ratios=remainder[:-1]/remainder[1:]
            slopes=(values-.4)/cs;richardson=(4*slopes[1]-slopes[0])/3
            target=float((reference.response_linear_series(1.)[key]-.4))
            maximum('response_first_PN_c4_ratio_deviation',np.max(abs(ratios-16)))
            maximum('response_first_PN_slope_Richardson_absolute',abs(richardson-target))
            if key!='distant_gravitational_areal':maximum('wrong_unchanged_inertia_slope_absolute',abs(richardson-12/35))
            order[key]=dict(remainders=remainder.tolist(),c4_ratios=ratios.tolist(),slopes=slopes.tolist(),Richardson_slope=float(richardson),analytic_slope=target)
        qs=np.array([x['proper_energy_mass_ratio'] for x in selected]);remainder=qs-reference.proper_volume_series(cs);ratios=remainder[:-1]/remainder[1:]
        slopes=(qs-1)/cs;richardson=(4*slopes[1]-slopes[0])/3
        maximum('proper_mass_c6_ratio_deviation',np.max(abs(ratios-64)))
        maximum('proper_mass_first_slope_Richardson_absolute',abs(richardson-.6))
        maximum('proper_mass_deficit_Newton_coefficient_absolute',abs(slopes[-1]-.6))
        order['proper_energy_mass']=dict(remainders=remainder.tolist(),c6_ratios=ratios.tolist(),Richardson_slope=float(richardson),Newton_deficit_coefficient=float(slopes[-1]))
        guard();copies_ok=all(hashlib.sha256((work/'executed-sources'/name).read_bytes()).hexdigest()==sha for name,sha in sources.items())
        verified=True;raw_ok=True;grid_ok=True
        for name,entry in arrays.items():
            path=ROOT/entry['path'];verified &= hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256']
            with np.load(path,allow_pickle=False) as saved:
                verified &= set(saved.files)==set(entry['shapes'])
                for key,shape in entry['shapes'].items():
                    verified &= list(saved[key].shape)==shape and np.all(np.isfinite(saved[key]))
                    verified &= np.array_equal(saved[key].view(np.uint64),expected[name][key].view(np.uint64))
                if name in jobs:
                    raw_ok &= np.array_equal(saved['states'][0].view(np.uint64),expected[name]['initial'].view(np.uint64))
                    grid_ok &= np.array_equal(saved['radius_fraction'].view(np.uint64),expected[name]['radius_fraction'].view(np.uint64))
        claims=('physical_lunar_mapping_certified','physical_accuracy_certified','harmonic_ADM_mapping_certified','baryon_EOS_inferred','finite_rotation_energy_implemented')
        confirmations=dict(sources_preserved=copies_ok,arrays_reverified=bool(verified),raw_initial_preserved=bool(raw_ok),grid_preserved=bool(grid_ok),
                           physical_claims_false=all(policy[key] is False for key in claims))
        failed=failures(metrics,confirmations,policy)
        report=dict(changes=policy['changes'],policy=policy,sources=sources,arrays=arrays,jobs=jobs,metrics=metrics,confirmations=confirmations,cases=results,
            order=order,passed=not failed,failed=failed,seconds=time.perf_counter()-start,
            environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
            runtime_changed=False,old_trajectories_reused=False,**{key:False for key in claims},
            limitations='Static incompressible acausal constant-energy-density sphere, linear-Omega only. Isotropic chart is not a qualified harmonic/ADM map. Baryon profiles are supplied static tracers, not an inferred EOS. Local apparent J/rate responses are not a physical inertia tensor. No finite-rotation energy, full PN orbit-spin dynamics, lunar mapping or tides. Numerical reference sensitivities and sampled checks are not rigorous accuracy bounds.')
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
