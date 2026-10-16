"""Fresh frozen-source smooth harmonic sphere audit, not a lunar runtime map."""
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
from scripts import independent_harmonic_reference as reference
from scripts.continuum_conventions import isotropic_geometry
from scripts.assess_metric_spin import failures

POLICY='scripts/harmonic-sphere-policy.json'
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


def flux_coefficient(s,c):
    u=np.sqrt(1-2*c*np.asarray(s)**2);n=(3*np.sqrt(1-2*c)-u)/2
    return np.asarray(s)**2*u*n


def audit(*,work=None,output=None):
    work=Path(work or ROOT/'.tools/rotation104').resolve();output=Path(output or ROOT/'docs/harmonic-sphere-validation.json').resolve()
    if not work.is_relative_to(ROOT) or not output.is_relative_to(ROOT):raise ValueError('Outputs must be inside project')
    if work.exists() or output.exists():raise FileExistsError('Fresh work/output paths required')
    check_sources();code_sources=source_hashes();policy=json.loads((ROOT/POLICY).read_text(encoding='utf-8'))
    primaries=primary_hashes(policy);sources={**code_sources,**primaries}
    work.mkdir(parents=True);output.parent.mkdir(parents=True,exist_ok=True)
    for name in sources:
        target=work/'executed-sources'/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((ROOT/name).read_bytes())
    start=time.perf_counter();arrays={};jobs={};expected={};metrics={k:0. for k in (*policy['maximum'],*policy['minimum'])}
    metrics['sampled_minimum_Jacobian']=1.
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
        if not sol.success or not np.array_equal(sol.t,grid[1:]) or not np.all(np.isfinite(sol.y)):raise ValueError('Incomplete/nonfinite harmonic radial IVP')
        states=np.vstack([initial.copy(),sol.y.T]);guard();save(name,dict(radius_fraction=grid,initial=initial,states=states))
        jobs[name]=dict(method=method,rtol=tol,atol=tol*policy['atol_over_rtol'],max_step=step,nfev=sol.nfev,seconds=time.perf_counter()-tick)
        return sol,states
    try:
        grid=np.linspace(0.,1.,policy['samples']);outer=np.array([1.,2.,10.]);cases=[]
        for index,c in enumerate(policy['compactnesses']):
            name='case-'+str(index)
            prod=run(name+'-production',np.array([1.,-0.]),grid,lambda s,z:harmonic.rhs(s,z,c),'DOP853',policy['production_rtol'],policy['production_max_radial_step'])
            refs=[run(name+'-reference-'+str(j),reference.centre_state(c),grid,lambda s,z:reference.riccati_rhs(s,z,c),'RK45',tol,policy['reference_max_radial_step']) for j,tol in enumerate(policy['reference_rtols'])]
            tight=run(name+'-tighter',reference.centre_state(c),grid,lambda s,z:reference.riccati_rhs(s,z,c),'DOP853',policy['tighter_rtol'],policy['tighter_max_radial_step'])
            chart=harmonic.match(prod[1][-1],c);geo=harmonic.interior_geometry(grid,prod[1],chart)
            matched=[reference.boundary(z[1][-1],c) for z in refs];profiles=[reference.profile(grid,z[1],m) for z,m in zip(refs,matched)]
            tightmap=reference.boundary(tight[1][-1],c);ht,hpt=reference.profile(grid,tight[1],tightmap)
            h=geo['harmonic_radius_fraction'];hp=geo['radius_derivative'];hr,hpr=profiles[1]
            maximum('reference_radius_profile',np.max(abs(h-hr)));maximum('reference_derivative_profile',np.max(abs(hp-hpr)))
            maximum('reference_levels_profile',max(np.max(abs(profiles[0][0]-hr)),np.max(abs(profiles[0][1]-hpr))))
            maximum('reference_tighter_profile',max(np.max(abs(ht-hr)),np.max(abs(hpt-hpr))))
            maximum('reference_matching_scale',abs(chart.scale-matched[1]['scale']))
            maximum('reference_residual_gauge',abs(chart.residual_gauge-matched[1]['residual_gauge']))
            metrics['sampled_minimum_Jacobian']=min(metrics['sampled_minimum_Jacobian'],float(np.min(hp)),float(np.min(geo['tangent_jacobian'])))
            maximum('matching_condition',chart.matching_condition)
            u=np.sqrt(1-2*c*grid*grid);n=(3*np.sqrt(1-2*c)-u)/2
            tangent=np.empty_like(grid);tangent[0]=matched[1]['scale'];tangent[1:]=hr[1:]/grid[1:]
            independent_weight=1/(u*tangent*tangent*hpr)
            maximum('current_volume_reference_relative',np.max(abs(geo['current_volume_weight']/independent_weight-1)))
            maximum('current_volume_pullback_absolute',np.max(abs(geo['current_volume_weight']*h*h*hp-grid*grid/u)))
            rawsecond=np.array([harmonic.rhs(float(s),z,c)[1] for s,z in zip(grid,prod[1])])
            hpp=chart.scale*(2*prod[1][:,1]+grid*rawsecond)
            flux_derivative=flux_coefficient(grid+1j*1e-20,c).imag/1e-20
            residual=flux_coefficient(grid,c)*hpp+flux_derivative*hp-2*n/u*h
            maximum('independent_self_adjoint_residual_scaled',np.max(abs(residual))/c)
            surface=harmonic.exterior_geometry(1.,chart)
            maximum('surface_value_derivative_matching',max(abs(h[-1]-surface['harmonic_radius_fraction']),abs(hp[-1]-surface['radius_derivative'])))
            maximum('surface_metric_matching',max(abs(geo[k][-1]-surface[k]) for k in ('metric_radial','metric_tangent','current_volume_weight','lapse')))
            ui=u[-1];upi=-2*c/ui;upe=c/ui
            gri=geo['metric_radial'][-1];gre=surface['metric_radial']
            derivative_in=gri*(-2*upi/ui-2*hpp[-1]/hp[-1])/hp[-1]
            derivative_out=gre*(-2*upe/ui-2*surface['radius_second_derivative']/surface['radius_derivative'])/surface['radius_derivative']
            maximum('surface_metric_first_derivative_matching',abs(derivative_in-derivative_out))
            maximum('regular_origin_isotropy',abs(geo['metric_radial'][0]-geo['metric_tangent'][0]))
            basis=harmonic.exterior_basis(outer,c);quadratures=[reference.vacuum_basis(outer,c,order) for order in (32,64)]
            for j in range(3):
                maximum('basis_independent_scaled',np.max(abs(basis[j]-quadratures[1][j])*outer**(j+2)))
                maximum('basis_levels_scaled',np.max(abs(quadratures[0][j]-quadratures[1][j])*outer**(j+2)))
            maximum('basis_vacuum_operator_scaled',np.max(abs(outer*(outer-2*c)*basis[2]+(2*outer-2*c)*basis[1]-2*basis[0])*outer**2))
            wrongscale=(1-c)/prod[1][-1,0]
            maximum('wrong_zero_gauge_derivative_jump',abs(wrongscale*sum(prod[1][-1])-1))
            iso=isotropic_geometry(grid,c);ip=iso['radius_derivative'];ih=iso['isotropic_radius_fraction']
            ipp=ip*(2*c*grid/u**2+2*c*grid/(u*(1+u)))
            wrongoperator=flux_coefficient(grid,c)*ipp+flux_derivative*ip-2*n/u*ih
            maximum('wrong_isotropic_harmonic_operator',np.max(abs(wrongoperator)))
            maximum('wrong_areal_harmonic_operator',np.max(abs(flux_derivative-2*n/u*grid)))
            maximum('wrong_growing_mode_origin',c)
            remainders=[]
            for order in (1,2):
                polynomial=reference.published_interior(grid,c,order)
                remainders.append(float(max(np.max(abs(h-polynomial[0])),np.max(abs(hp-polynomial[1])))))
            save(name+'-geometry',dict(radius_fraction=grid,harmonic_radius=h,radius_derivative=hp,independent_radius=hr,independent_derivative=hpr,
                geometry=np.stack(list(geo.values()),axis=1),harmonic_operator_residual=residual))
            save(name+'-vacuum',dict(radius_fraction=outer,basis=np.stack(basis,axis=1),quadrature=np.stack(quadratures[1],axis=1),tail_bounds=np.stack(harmonic.basis_tail_bounds(outer,c),axis=1)))
            cases.append(dict(compactness=c,scale=chart.scale,residual_gauge=chart.residual_gauge,matching_condition=chart.matching_condition,
                surface_radius=float(h[-1]),surface_derivative=float(hp[-1]),reference_matching=matched[1],published_remainders=remainders))
            print(f'{name} C={c}: global harmonic chart checks complete',flush=True)
        selected=[cases[i] for i in policy['order_cases']];r=np.array([z['published_remainders'] for z in selected]);ratios=r[:-1]/r[1:]
        maximum('first_order_c4_ratio_deviation',np.max(abs(ratios[:,0]-16)))
        maximum('second_order_c6_ratio_deviation',np.max(abs(ratios[:,1]-64)))
        smallest=selected[-1];maximum('residual_gauge_second_coefficient',abs(smallest['residual_gauge']/smallest['compactness']**2+4/35))
        guard();copy_ok=all(hashlib.sha256((work/'executed-sources'/name).read_bytes()).hexdigest()==sha for name,sha in sources.items())
        verified=True;raw_ok=True;grid_ok=True
        for name,entry in arrays.items():
            p=ROOT/entry['path'];verified &= hashlib.sha256(p.read_bytes()).hexdigest()==entry['sha256']
            with np.load(p,allow_pickle=False) as saved:
                verified &= set(saved.files)==set(entry['shapes'])
                for key,shape in entry['shapes'].items():
                    verified &= list(saved[key].shape)==shape and np.all(np.isfinite(saved[key]))
                    verified &= np.array_equal(saved[key].view(np.uint64),expected[name][key].view(np.uint64))
                if name in jobs:
                    raw_ok &= np.array_equal(saved['states'][0].view(np.uint64),expected[name]['initial'].view(np.uint64))
                    grid_ok &= np.array_equal(saved['radius_fraction'].view(np.uint64),expected[name]['radius_fraction'].view(np.uint64))
        claims=('physical_lunar_mapping_certified','physical_accuracy_certified','ADM_SSC_mapping_certified','PN_tensor_certified','runtime_changed')
        flags=dict(sources_preserved=copy_ok,arrays_reverified=bool(verified),raw_initial_preserved=bool(raw_ok),grid_preserved=bool(grid_ok),physical_claims_false=all(policy[k] is False for k in claims))
        failed=failures(metrics,flags,policy);report=dict(changes=policy['changes'],policy=policy,sources=sources,arrays=arrays,jobs=jobs,metrics=metrics,confirmations=flags,cases=cases,
            order_ratios=ratios.tolist(),passed=not failed,failed=failed,seconds=time.perf_counter()-start,**{k:False for k in claims},
            old_trajectories_reused=False,environment=dict(python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__),
            limitations='Static incompressible acausal energy sphere, selected globally smooth harmonic chart. Domain C>=1e-4 excludes physical Moon compactness. No ADM/SSC centre map, physical PN inertia tensor, finite rotation energy or tides. Numerical reference sensitivity and sampled Jacobian checks are not rigorous physical accuracy bounds.')
        text=json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        with (work/'report.json').open('x',encoding='utf-8') as f:f.write(text)
        with output.open('x',encoding='utf-8') as f:f.write(text)
        if failed:raise ValueError('Predeclared criteria failed: '+', '.join(failed))
        return report
    except Exception as error:
        (work/'failure.json').write_text(json.dumps(dict(passed=False,error=repr(error),sources=sources,arrays=arrays,jobs=jobs,metrics=metrics),indent=2)+'\n',encoding='utf-8')
        raise


if __name__=='__main__':
    result=audit();print(json.dumps(dict(passed=result['passed'],metrics=result['metrics'],order_ratios=result['order_ratios'],jobs=len(result['jobs']),arrays=len(result['arrays'])),indent=2))
