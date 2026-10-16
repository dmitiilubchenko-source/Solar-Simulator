"""Source-frozen Komar metric/stress and ordered spin-current audit."""
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
from scripts import continuum_stress as stress
from scripts import fluid_spin as spin
from scripts import independent_stress_reference as reference
from scripts.independent_conventions_reference import gauss_nodes
from scripts.continuum_sphere import Sphere, background
from scripts.assess_metric_spin import failures

POLICY='scripts/continuum-stress-policy.json'
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
    work=Path(work or ROOT/'.tools/rotation98').resolve()
    output=Path(output or ROOT/'docs/continuum-stress-validation.json').resolve()
    if not work.is_relative_to(ROOT) or not output.is_relative_to(ROOT):raise ValueError('Outputs must be inside project')
    if work.exists() or output.exists():raise FileExistsError('Fresh work/output paths required')
    check_sources();code_sources=source_hashes();policy=json.loads((ROOT/POLICY).read_text(encoding='utf-8'))
    primaries=primary_hashes(policy);sources={**code_sources,**primaries}
    work.mkdir(parents=True);output.parent.mkdir(parents=True,exist_ok=True)
    for name in sources:
        target=work/'executed-sources'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
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
    def run(name,initial,nodes,function,method,tol,max_step):
        guard();tick=time.perf_counter()
        sol=solve_ivp(function,(0.,1.),initial,t_eval=nodes[1:],dense_output=True,method=method,
            rtol=tol,atol=tol*policy['atol_over_rtol'],max_step=max_step)
        if not sol.success or not np.array_equal(sol.t,nodes[1:]) or not np.all(np.isfinite(sol.y)):
            raise ValueError('Incomplete/nonfinite spin radial integration')
        states=np.vstack([initial.copy(),sol.y.T]);guard();save(name,dict(radius_fraction=nodes,initial=initial,states=states))
        jobs[name]=dict(method=method,rtol=tol,atol=tol*policy['atol_over_rtol'],max_step=max_step,nfev=sol.nfev,seconds=time.perf_counter()-tick)
        return sol,states
    try:
        grid=np.linspace(0.,1.,policy['samples']);cases=[]
        for i,c in enumerate(policy['compactnesses']):
            name='case-'+str(i)
            body=Sphere(policy['gravitational_mass_kg'],policy['areal_radius_m'],policy['gravitational_constant'],
                np.sqrt(policy['gravitational_constant']*policy['gravitational_mass_kg']/policy['areal_radius_m']/c))
            mass=stress.komar_measures(grid,body);metric=reference.metric_komar_charge(grid,c)
            maximum('komar_metric_charge_absolute',np.max(abs(mass['komar_metric_charge_kg']/body.gravitational_mass_kg-metric)))
            prod=run(name+'-spin',np.array([1.,-0.]),grid,lambda s,z:spin.rhs(s,z,c),'DOP853',policy['production_rtol'],policy['production_max_radial_step'])
            refs=[run(name+'-reference-'+str(j),np.array([0.,-0.]),grid,lambda s,z:reference.spin_log_rhs(s,z,c),'RK45',tol,policy['reference_max_radial_step']) for j,tol in enumerate(policy['reference_rtols'])]
            tight=run(name+'-tighter',np.array([0.,-0.]),grid,lambda s,z:reference.spin_log_rhs(s,z,c),'DOP853',policy['tighter_rtol'],policy['tighter_max_radial_step'])
            matched=spin.boundary(prod[1][-1],c);a=matched['inertia_factor'];norm=matched['omega_over_central'];h=prod[1][:,0]/norm
            profiles=[reference.normalized_profile(z[1],z[1][-1]) for z in refs]
            htight=reference.normalized_profile(tight[1],tight[1][-1])
            arefs=[z[1][-1,0]/(2*c*(3+z[1][-1,0])) for z in refs];atight=tight[1][-1,0]/(2*c*(3+tight[1][-1,0]))
            maximum('spin_reference_inertia_absolute',abs(a-arefs[1]))
            maximum('spin_reference_profile_absolute',np.max(abs(h-profiles[1])))
            maximum('spin_reference_levels_absolute',max(abs(arefs[0]-arefs[1]),np.max(abs(profiles[0]-profiles[1]))))
            maximum('spin_reference_tighter_absolute',max(abs(arefs[1]-atight),np.max(abs(profiles[1]-htight))))
            quadratures=[];term_integrals=[];komars=[];controls=[]
            for n in policy['quadrature_orders']:
                nodes,weights=gauss_nodes(n);raw=prod[0].sol(nodes).T;hp=raw[:,0]/norm
                hr=reference.normalized_profile(refs[1][0].sol(nodes).T,refs[1][1][-1])
                terms=stress.spin_terms(nodes,hp,c);integrated={key:float(np.dot(weights,value)) for key,value in terms.items()}
                independent=float(np.dot(weights,reference.direct_inertia_integrand(nodes,hr,c)))
                maximum('independent_matter_integral_absolute',abs(independent-integrated['full']))
                maximum('matter_integral_inertia_absolute',abs(a-integrated['full']))
                maximum('telescoping_integrand_absolute',np.max(abs(sum(terms[key] for key in ('newton','pressure','proper_volume','lapse','frame_profile'))-terms['full'])))
                m=stress.komar_measures(nodes,body);bg=background(nodes,c);u=np.sqrt(bg['radial_inverse_metric']);p=bg['pressure_ratio'];lapse=bg['lapse'];base=2*nodes**4
                k=float(np.dot(weights,m['komar_mass_rate_kg'])/body.gravitational_mass_kg);komars.append(k)
                energy=float(np.dot(weights,m['redshifted_energy_rate_kg'])/body.gravitational_mass_kg)
                wrongmass_no_lapse=float(np.dot(weights,3*nodes**2*(1+3*p)/u))
                wrongmass_no_volume=float(np.dot(weights,3*nodes**2*lapse*(1+3*p)))
                wrongspin=dict(no_pressure=float(np.dot(weights,base*hp/(u*lapse))),
                    no_lapse=float(np.dot(weights,base*hp*(1+p)/u)),
                    no_profile=float(np.dot(weights,base*(1+p)/(u*lapse))),paired=integrated['paired_omission'])
                maximum('komar_integral_relative',abs(k-1))
                maximum('wrong_no_pressure_komar_relative',abs(energy-1))
                maximum('wrong_no_lapse_komar_relative',abs(wrongmass_no_lapse-1))
                maximum('wrong_no_volume_komar_relative',abs(wrongmass_no_volume-1))
                maximum('wrong_no_pressure_spin_absolute',abs(a-wrongspin['no_pressure']))
                maximum('wrong_no_lapse_spin_absolute',abs(a-wrongspin['no_lapse']))
                maximum('wrong_no_profile_spin_absolute',abs(a-wrongspin['no_profile']))
                maximum('wrong_paired_omission_spin_absolute',abs(a-wrongspin['paired']))
                save(name+'-quadrature-'+str(n),dict(radius_fraction=nodes,weights=weights,
                    normalized_profile_production=hp,normalized_profile_reference=hr,spin_terms=np.stack(list(terms.values()),axis=1),
                    mass_terms=np.stack(list(m.values()),axis=1),independent_metric_charge=reference.metric_komar_charge(nodes,c)))
                quadratures.append(dict(order=n,full=integrated['full'],reference_full=independent,komar=k,redshifted_energy=energy))
                term_integrals.append(integrated);controls.append(wrongspin)
            maximum('matter_integral_levels_absolute',abs(quadratures[0]['full']-quadratures[1]['full']))
            maximum('komar_integral_levels_relative',abs(komars[0]-komars[1]))
            radial_terms=stress.spin_terms(grid,h,c)
            save(name+'-radial-diagnostics',dict(radius_fraction=grid,normalized_profile_production=h,normalized_profile_reference=profiles[1],
                spin_terms=np.stack(list(radial_terms.values()),axis=1),mass_terms=np.stack(list(mass.values()),axis=1),independent_metric_charge=metric))
            cases.append(dict(compactness=c,inertia_factor=a,reference_inertias=[float(v) for v in arefs],tighter_inertia=float(atight),
                quadratures=quadratures,term_integrals=term_integrals,omission_controls=controls,
                SI=dict(mass_kg=body.gravitational_mass_kg,areal_radius_m=body.areal_radius_m,G=body.gravitational_constant,c=body.light_speed_m_s)))
            print(f'{name} C={c}: metric/stress/current checks complete',flush=True)
        selected=[cases[i] for i in policy['order_cases']];cs=np.array([z['compactness'] for z in selected]);order={}
        for key,coefficient in reference.term_linear_coefficients().items():
            values=np.array([z['term_integrals'][1][key] for z in selected]);slopes=values/cs
            richardson=(4*slopes[1]-slopes[0])/3;remainder=values-coefficient*cs;ratios=remainder[:-1]/remainder[1:]
            maximum('term_first_PN_slope_Richardson_absolute',abs(richardson-coefficient))
            maximum('term_first_PN_c4_ratio_deviation',np.max(abs(ratios-16)))
            order[key]=dict(analytic_slope=coefficient,Richardson_slope=float(richardson),c4_ratios=ratios.tolist(),remainders=remainder.tolist())
        actual=np.array([z['inertia_factor'] for z in selected]);wrong=np.array([z['term_integrals'][1]['paired_omission'] for z in selected])
        wrongslopes=(wrong-.4)/cs;richardson=(4*wrongslopes[1]-wrongslopes[0])/3
        coefficients=reference.second_order_coefficients();correct_second=(actual[-1]-.4-12/35*cs[-1])/cs[-1]**2
        wrong_second=(wrong[-1]-.4-12/35*cs[-1])/cs[-1]**2;difference=(wrong[-1]-actual[-1])/cs[-1]**2
        maximum('paired_omission_first_PN_slope_Richardson_absolute',abs(richardson-12/35))
        maximum('paired_omission_second_coefficient_absolute',abs(wrong_second-coefficients['paired_omission']))
        maximum('paired_omission_difference_coefficient_absolute',abs(difference-coefficients['difference']))
        maximum('correct_second_coefficient_absolute',abs(correct_second-coefficients['correct']))
        maximum('wrong_paired_second_coefficient_gap',abs(wrong_second-coefficients['correct']))
        energy=selected[-1]['quadratures'][1]['redshifted_energy']
        maximum('no_pressure_komar_first_slope_absolute',abs((1-energy)/cs[-1]-.6))
        order['paired_omission']=dict(Richardson_first_slope=float(richardson),correct_second=float(correct_second),wrong_second=float(wrong_second),
            difference_second=float(difference),analytic_coefficients=coefficients,wrong_minus_correct=(wrong-actual).tolist())
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
        claims=('physical_lunar_mapping_certified','physical_accuracy_certified','invariant_field_spin_split_certified','PN_tensor_certified','finite_rotation_energy_implemented')
        confirmations=dict(sources_preserved=copies_ok,arrays_reverified=bool(verified),raw_initial_preserved=bool(raw_ok),grid_preserved=bool(grid_ok),physical_claims_false=all(policy[k] is False for k in claims))
        failed=failures(metrics,confirmations,policy)
        report=dict(changes=policy['changes'],policy=policy,sources=sources,arrays=arrays,jobs=jobs,metrics=metrics,confirmations=confirmations,cases=cases,order=order,
            passed=not failed,failed=failed,seconds=time.perf_counter()-start,environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
            runtime_changed=False,old_trajectories_reused=False,**{k:False for k in claims},
            limitations='Regular incompressible acausal spherical benchmark and linear-Omega only. Ordered current pieces are bookkeeping, not invariant field-spin contributions. Paired lapse/profile omissions cancel first-order integrated slope but have incorrect second coefficient. No full PN inertia tensor, harmonic/ADM centre/SSC map, finite-rotation energy, lunar calibration or tides. Quadrature/ODE sensitivity and sampled consistency are not rigorous physical accuracy bounds.')
        text=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        with (work/'report.json').open('x',encoding='utf-8') as f:f.write(text)
        with output.open('x',encoding='utf-8') as f:f.write(text)
        if failed:raise ValueError('Predeclared criteria failed: '+', '.join(failed))
        return report
    except Exception as error:
        (work/'failure.json').write_text(json.dumps(dict(passed=False,error=repr(error),sources=sources,arrays=arrays,jobs=jobs,metrics=metrics),indent=2)+'\n',encoding='utf-8')
        raise


if __name__=='__main__':
    result=audit();print(json.dumps(dict(passed=result['passed'],metrics=result['metrics'],order=result['order'],jobs=len(result['jobs']),arrays=len(result['arrays'])),indent=2))
