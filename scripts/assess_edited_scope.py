"""Actual-IC elliptic checks for edited sandbox pairs; never runtime physics."""
import argparse
from dataclasses import replace
from decimal import Decimal as D,localcontext
from importlib import import_module
import json
from math import pi,sqrt
from pathlib import Path
from time import perf_counter

import numpy as np
import scipy

from scripts.assess_kepler_phase import decimal_relative,differences,maximum
from scripts.assess_sandbox_limits import scenario,elliptic_reference,balances,R
from scripts.assess_sandbox_planets import states
from scripts.kepler_reference import propagate
from scripts.newton_year import ROOT,hashes
from solar_simulator.experiment import reset
from solar_simulator.sandbox import branch_experiment,to_branch_document,from_branch_document
from solar_simulator.simulation import G
from solar_simulator.storage import to_document,from_document
from solar_simulator.time_control import advance_towards
from solar_simulator.vector3 import Vector3

CASES = ('mass-double','slow-velocity','eccentric-095','add-companion','position-edit')


def fixture(name,backend):
    if name not in CASES:raise ValueError('Undeclared edited case')
    if name=='position-edit':
        parent,_ = scenario('mass-double',backend)
        body = parent.bodies[1]
        position = body.position.add(Vector3(.03*R,-.02*R,.04*R))
        branch = branch_experiment(parent,replacements=((body.name,replace(body,position=position)),))
        q = states(branch.child.bodies);rho = q[1]-q[0]
        mu = G*sum(b.mass for b in branch.child.bodies)
        a = 1/(2/np.linalg.norm(rho[:3])-rho[3:]@rho[3:]/mu)
        period = 2*pi*sqrt(a**3/mu)
    else:
        parent,branch = scenario(name,backend)
        _,period,_ = elliptic_reference([0.],branch.child.bodies)
    return parent,branch,np.linspace(0.,period,33)


def reference(seed,times):
    if (len(seed.bodies)!=2 or seed.settings.physics!='newtonian' or seed.settings.figures
            or seed.time!=0 or seed.origin is not None or seed.rotations
            or any(b.radius or b.spin.magnitude() for b in seed.bodies)):
        raise ValueError('Expected fresh untagged Newtonian point pair')
    times = np.asarray(times)
    if times.ndim!=1 or len(times)<2 or times[0]!=0 or not np.isfinite(times).all() or not (np.diff(times)>0).all():
        raise ValueError('Expected increasing finite times from zero')
    with localcontext() as context:
        context.prec = 110
        q = states(seed.bodies);initial = decimal_relative(q)
        mu = D.from_float(G)*sum(D.from_float(float(b.mass)) for b in seed.bodies)
        values,precision,export = [],[],[]
        for time in times:
            high = propagate(initial[:3],initial[3:],mu,D.from_float(float(time)),precision=100)
            low = propagate(initial[:3],initial[3:],mu,D.from_float(float(time)),precision=70)
            precision.append(differences(low,high))
            rounded = tuple(tuple(D.from_float(float(x)) for x in group) for group in high)
            export.append(differences(rounded,high))
            values.append(high)
        if values[0]!=(initial[:3],initial[3:]):raise ValueError('Oracle t0 differs from actual IC')
    uncertainty = maximum(precision)
    passed = uncertainty['position_metres']<1e-6 and uncertainty['velocity_m_per_s']<1e-12
    return values,dict(precision70_vs100=uncertainty,float64_export=maximum(export),
        exact_initial=True,checks_passed=passed)


def trajectory(seed,times):
    current = from_document(to_document(seed))
    values=[];packets=0;checkpoint_exact=False
    for index,target in enumerate(times):
        while current.time<target:
            current = advance_towards(current,float(target),20);packets+=1
        if current.time!=target:raise ValueError('Production epoch differs')
        values.append(states(current.bodies))
        if index==16:
            restored = from_document(to_document(current))
            a = advance_towards(current,float(times[17]),20)
            b = advance_towards(restored,float(times[17]),20)
            if to_document(a)!=to_document(b):raise ValueError('Checkpoint continuation differs')
            current = restored;checkpoint_exact=True
    if not np.isfinite(values).all():raise ValueError('Nonfinite trajectory')
    if to_document(reset(current))!=to_document(seed):raise ValueError('Reset did not preserve the child start')
    return np.array(values),dict(packets=packets,checkpoint_continue_exact=checkpoint_exact,exact_epochs=True)


def metrics(values,expected,masses):
    if values.shape!=(len(expected),2,6) or not len(expected) or not np.isfinite(values).all():
        raise ValueError('Candidate/reference shape or finite values mismatch')
    with localcontext() as context:
        context.prec = 110
        error = maximum([differences((decimal_relative(q)[:3],decimal_relative(q)[3:]),ref)
            for q,ref in zip(values,expected)])
    q0=values[0]
    def bodies(q):
        from solar_simulator.simulation import Body
        return [Body(str(i),float(m),Vector3(*map(float,row[:3])),Vector3(*map(float,row[3:])))
            for i,(m,row) in enumerate(zip(masses,q))]
    e0,p0,j0 = balances(bodies(q0))
    pscale = np.sum(masses*np.linalg.norm(q0[:,3:],axis=1))
    norms = []
    for q in values:
        e,p,j = balances(bodies(q))
        norms.append((abs((e-e0)/e0),float(np.linalg.norm(p-p0)/pscale),float(np.linalg.norm(j-j0)/np.linalg.norm(j0))))
    drift = np.max(norms,axis=0)
    return dict(**error,relative_energy_drift=float(drift[0]),scaled_momentum_drift=float(drift[1]),
        relative_angular_momentum_drift=float(drift[2]))


def run(output):
    output = Path(output).resolve()
    if output.with_suffix('.json').exists() or output.with_suffix('.npz').exists():
        raise ValueError('Use a fresh output path')
    output.parent.mkdir(parents=True,exist_ok=True)
    prior = json.loads((ROOT/'docs/sandbox-limits-validation.json').read_bytes())
    if hashes(prior['source_sha256'])!=prior['source_sha256']:
        raise ValueError('Historical sandbox sources changed')
    source_paths = [p.relative_to(ROOT).as_posix() for p in (ROOT/'src/solar_simulator').glob('*.py')]
    source_paths += ['scripts/'+p+'.py' for p in ('assess_edited_scope','assess_sandbox_limits',
        'assess_kepler_phase','kepler_reference','assess_sandbox_planets','newton_year')]
    source_paths += ['docs/edited-system-scope-protocol.md','tests/test_edited_scope.py']
    sources = hashes(source_paths)
    input_paths = ['docs/sandbox-limits-validation.json','docs/solar-sandbox-strict-checkpoint.json']
    inputs = hashes(input_paths)
    native_paths = [Path(import_module(n).__file__) for n in ('solar_native','solar_native.solar_native')]
    native = hashes(native_paths)
    if native[str(native_paths[1])]!='19327a3e4ff91d22ba7f6c181c0f37f4a134b16cb5d441cbc899a220d4e310f7':
        raise ValueError('Native binary differs from qualified build')
    document = dict(protocol='docs/edited-system-scope-protocol.md',source_sha256=sources,
        input_sha256=inputs,native_sha256=native,units='SI',physics='Newtonian point pairs',
        samples=33,results={},complete=False,general_release=False,
        environment=dict(numpy=np.__version__,scipy=scipy.__version__))
    arrays={}
    def save():
        np.savez_compressed(output.with_suffix('.npz'),**arrays)
        document['npz_sha256'] = hashes([output.with_suffix('.npz')]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(document,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    try:
        for name in CASES:
            for backend in ('python','rust'):
                key=name+'_'+backend
                parent,branch,times = fixture(name,backend)
                before = to_document(parent);bundle = to_branch_document(branch)
                seed = from_branch_document(bundle).child
                start=perf_counter();expected,ref_stats = reference(seed,times)
                ref_stats['wall_seconds']=perf_counter()-start
                start=perf_counter();values,stats=trajectory(seed,times)
                stats['wall_seconds']=perf_counter()-start
                row=metrics(values,expected,np.array([b.mass for b in seed.bodies]))
                p=values[:,:,:3];v=values[:,:,3:];m=np.array([b.mass for b in seed.bodies]);weights=m/m.sum()
                center=np.sum(p*weights[None,:,None],axis=1)
                drift=np.sum(v[0]*weights[:,None],axis=0)
                row['center_of_mass_error_metres']=float(np.linalg.norm(center-center[0]-times[:,None]*drift,axis=1).max())
                with localcontext() as context:
                    context.prec=110
                    nominal=None
                    if name!='position-edit':
                        old,_,_=elliptic_reference(times,seed.bodies)
                        nominal=maximum([differences((tuple(D.from_float(float(x)) for x in q[:3]),
                            tuple(D.from_float(float(x)) for x in q[3:])),ref) for q,ref in zip(old,expected)])
                if to_document(parent)!=before or to_branch_document(branch)!=bundle:
                    raise ValueError('Parent or original child changed')
                row.update(reference=ref_stats,production=stats,old_nominal_reference_difference=nominal,
                    initial=values[0].tolist(),masses_kg=m.tolist(),times_seconds=times.tolist(),
                    parent_preserved=True,origin=None,
                    checks_passed=bool(ref_stats['checks_passed'] and row['position_metres']<10
                        and row['velocity_m_per_s']<1e-5 and row['center_of_mass_error_metres']<.01
                        and max(row[k] for k in ('relative_energy_drift','scaled_momentum_drift','relative_angular_momentum_drift'))<1e-10))
                arrays[key]=values;arrays[key+'_times']=times
                arrays[key+'_reference_export']=np.array(expected,dtype=float)
                document['results'][key]=row;save()
                print(key,row['checks_passed'],row['position_metres'],row['velocity_m_per_s'],flush=True)
        if hashes(source_paths)!=sources or hashes(input_paths)!=inputs or hashes(native_paths)!=native:
            raise ValueError('Source/input/actual binary changed during audit')
        document.update(complete=True,source_input_native_unchanged=True,
            checks_passed=all(r['checks_passed'] for r in document['results'].values()))
        save()
    except Exception as error:
        document['failure']=dict(type=type(error).__name__,message=str(error));save();raise
    return document


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not run(args.output)['checks_passed']:raise RuntimeError('Declared criteria failed; report retained')


if __name__=='__main__':main()
