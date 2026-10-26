"""Assess actual qualification375 jobs against preregistered independent criteria."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT),str(ROOT/'src')]
from scripts.qualify_current_runtime375 import protocol, PROTOCOL, PROTOCOL_SHA, WORK, write_json, sources as loaded_sources
from scripts.assess_dense_jpl import validate_reference, residuals
from scripts.fetch_ephemerides import parse_result

REPORT = 'docs/current-runtime-375-validation.json'
ARRAYS = 'scripts/validation/current-runtime-375.npz'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bits(a,b):
    a,b = np.asarray(a),np.asarray(b)
    return a.shape==b.shape and a.dtype==b.dtype and a.tobytes()==b.tobytes()


def errors(a,b):
    delta = np.asarray(a)-np.asarray(b)
    return dict(position_metres=float(np.linalg.norm(delta[...,:3],axis=-1).max()),
                velocity_m_per_s=float(np.linalg.norm(delta[...,3:],axis=-1).max()))


def numerical(actual,reference,names,c):
    earth,moon = names.index('Earth'),names.index('Moon')
    per_body = {name:errors(actual[:,i],reference[:,i]) for i,name in enumerate(names)}
    relative = errors(actual[:,moon]-actual[:,earth],reference[:,moon]-reference[:,earth])
    passed = all(row['position_metres']<c['per_body_position_m'] and
                 row['velocity_m_per_s']<c['per_body_velocity_m_s'] for row in per_body.values())
    passed &= relative['position_metres']<c['earth_moon_position_m'] and relative['velocity_m_per_s']<c['earth_moon_velocity_m_s']
    return dict(per_body=per_body,earth_moon=relative,checks_passed=bool(passed))


def sensitivity(a,b,names,c):
    earth,moon = names.index('Earth'),names.index('Moon')
    absolute = errors(a,b)
    relative = errors(a[:,moon]-a[:,earth],b[:,moon]-b[:,earth])
    return dict(all_bodies=absolute,earth_moon=relative,checks_passed=
        absolute['position_metres']<c['sensitivity_per_body_position_m'] and
        relative['position_metres']<c['sensitivity_earth_moon_position_m'])


def packet_grid(times,size):
    result=[];time=0.
    for target in times:
        while time<target:
            end=min(float(target),time+3600*size)
            result.append([time,end]);time=end
    return np.asarray(result)


def load_job(version,p):
    directory = WORK/('run-'+version)
    row=json.loads((directory/'receipt.json').read_bytes())
    if (row['protocol_sha256']!=PROTOCOL_SHA or not row['solver_executed'] or
            row['driver_sha256']!=sha(ROOT/'scripts/qualify_current_runtime375.py')):
        raise ValueError('Changed or unexecuted scientific job375: '+version)
    if version!='reference':
        if sha(directory/'outputs.npz')!=row['outputs_sha256']:
            raise ValueError('Changed scientific output375: '+version)
        with np.load(directory/'outputs.npz',allow_pickle=False) as data:
            arrays={k:data[k].copy() for k in data.files}
        expected_commit=p['runtime_commit'] if version=='current' else p['accepted_commit']
        if row['runtime_commit']!=expected_commit:
            raise ValueError('Wrong runtime commit375')
        # Actual imported runtime module/data hashes must match the designated Git commit.
        for name,expected in row['source_sha256'].items():
            if name.startswith(('src/solar_simulator/','rust/solar_core/','rust/solar_native/')):
                raw=subprocess.check_output(['git','show',expected_commit+':'+name],cwd=ROOT)
                checkout=ROOT if version=='current' or name.startswith('rust/') else WORK/'accepted032'
                working=(checkout/name).read_bytes()
                if hashlib.sha256(working).hexdigest()!=expected:
                    raise ValueError('Job source changed after execution: '+name)
                # This legal notice is checkout-translated by Git. It is not a
                # numerical input. All Python/JSON/Rust bytes remain exact.
                if name=='src/solar_simulator/data/ERFA-LICENSE.txt':
                    same=raw.replace(b'\r\n',b'\n')==working.replace(b'\r\n',b'\n')
                else:
                    same=hashlib.sha256(raw).hexdigest()==expected
                if not same:
                    raise ValueError('Job did not execute designated runtime bytes: '+name)
        return row,arrays
    return row,{}


def assess():
    p=protocol();c=p['criteria']
    if (ROOT/REPORT).exists() or (ROOT/ARRAYS).exists():
        raise FileExistsError('Preserve qualification375 evidence')
    for name,expected in {**p['input_sha256'],**p['raw_jpl_sha256']}.items():
        if sha(ROOT/name)!=expected:
            raise ValueError('Changed preregistered scientific input: '+name)
    current,a=load_job('current',p);old,b=load_job('accepted032',p)
    ref=json.loads((WORK/'run-reference/receipt.json').read_bytes())
    if not ref['solver_executed'] or ref['protocol_sha256']!=PROTOCOL_SHA:
        raise ValueError('Missing fresh independent references375')
    from scripts.assess_sandbox_models import load_inputs
    from solar_simulator.ephemerides import RESOLVED_IDS
    initial,origin,_,_,_=load_inputs();names=[x.name for x in initial]
    times=(np.asarray(p['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    holdout=np.asarray(p['holdout_times_seconds'])
    for data in (a,b):
        if not bits(data['times'],times) or not bits(data['holdout_times'],holdout):
            raise ValueError('Changed scientific epoch grid375')
    if not bits(a['initial'],b['initial']) or not bits(a['masses'],b['masses']):
        raise ValueError('Different regression initial conditions375')
    if current['environment']!=old['environment'] or current['environment']!=ref['environment']:
        raise ValueError('Different numerical environments375')
    reference={};data={}
    for version,arrays in [('current',a),('accepted032',b)]:
        data.update({version+'_'+key:value for key,value in arrays.items()})
    for key,grid in [('annual',times),('holdout',holdout)]:
        file=WORK/'run-reference'/(key+'.npz')
        if sha(file)!=ref['results'][key]['output_sha256']:
            raise ValueError('Changed independent reference375')
        with np.load(file,allow_pickle=False) as saved:
            if not bits(saved['times'],grid) or set(saved.files)!={'times','level_0','level_1'}:
                raise ValueError('Incomplete reference sensitivity375')
            for n in ('level_0','level_1'):
                data['reference_'+key+'_'+n]=saved[n].copy()
            reference[key]=saved['level_1'].copy()
        convergence=ref['results'][key]['convergence']
        if (convergence['all_bodies']['maximum_position_metres']>=c['reference_position_m'] or
                convergence['moon_relative_to_earth']['maximum_position_metres']>=c['reference_earth_moon_position_m']):
            raise ValueError('Fresh reference not converged375')
    dense=json.loads((ROOT/'docs/qualification-grid-reference.json').read_bytes())
    expected=validate_reference(dense,origin,names,RESOLVED_IDS,p['epochs_jd_tdb'])
    for body in dense['bodies']:
        raw=[];offset=0
        for request in body['requests']:
            name=f".tools/qualification144/jpl-batches/horizons-{body['id']}-{offset:03d}.json"
            raw.extend(parse_result(json.loads((ROOT/name).read_bytes()),body['id'],request['epochs_jd_tdb']))
            offset+=len(request['epochs_jd_tdb'])
        if raw!=body['states']:
            raise ValueError('JPL matrix differs from actual raw responses375')
    data['jpl_values']=expected
    overlap=errors(a['initial'],expected[0])
    if overlap['position_metres']>.01 or overlap['velocity_m_per_s']>1e-8:
        raise ValueError('Initial JPL coordinate/time/unit overlap failed375')
    results={};gates={};sensitivity_rows={};regression={}
    for backend in ('python','rust'):
        for suffix in ('strict20','strict10','standard20','holdout20'):
            key=backend+'_'+suffix
            grid=holdout if suffix=='holdout20' else times
            size=10 if suffix=='strict10' else 20
            values=a[key+'_values'];job=current['jobs'][key]
            if not bits(a[key+'_packets'],packet_grid(grid,size)):
                raise ValueError('Actual packet schedule differs375: '+key)
            settings=dict(p['settings'],backend=backend,rtol=1e-13 if suffix=='standard20' else 3e-14)
            if job['settings']!=settings or job['rtol']!=settings['rtol'] or job['packet_max_steps']!=size:
                raise ValueError('Actual settings differ375: '+key)
            if (backend=='rust')!=(job['native_force_calls']>0):
                raise ValueError('Actual native force proof missing375')
            row=numerical(values,reference['holdout' if suffix=='holdout20' else 'annual'],names,c)
            row['energy_residual']=job['relative_energy_residual']
            row['energy_check_passed']=row['energy_residual']<c['energy_residual']
            if suffix!='holdout20':
                row['jpl']=residuals(values,expected,names,p['epochs_jd_tdb'])
            results[key]=row
            if suffix!='standard20':
                gates[key]=bool(row['checks_passed'] and row['energy_check_passed'] and
                    (suffix=='holdout20' or row['jpl']['physical_goals_passed']))
        for kind,suffix in [('tolerance','standard20'),('packet','strict10')]:
            key=backend+'_'+kind
            sensitivity_rows[key]=sensitivity(a[backend+'_strict20_values'],a[backend+'_'+suffix+'_values'],names,c)
            gates[key]=sensitivity_rows[key]['checks_passed']
        for suffix in ('strict20','holdout20'):
            key=backend+'_'+suffix
            regression[key]=dict(values_bitwise=bits(a[key+'_values'],b[key+'_values']),
                packets_bitwise=bits(a[key+'_packets'],b[key+'_packets']),
                final_document_exact=bool(a[key+'_final_document']==b[key+'_final_document']),
                difference=errors(a[key+'_values'],b[key+'_values']))
            gates['regression_'+key]=all(regression[key][k] for k in ('values_bitwise','packets_bitwise','final_document_exact'))
    with np.load(ROOT/'.tools/qualification138/production139.npz',allow_pickle=False) as previous:
        stored=dict(current_rust_bitwise=bits(a['rust_strict20_values'],previous['rust_tighter']),
            accepted032_rust_bitwise=bits(b['rust_strict20_values'],previous['rust_tighter']),
            current_difference=errors(a['rust_strict20_values'],previous['rust_tighter']))
    edited=[]
    for row in current['sandbox']:
        key=row['backend']+'_'+row['name']
        old_row=next(x for x in old['sandbox'] if (x['name'],x['backend'])==(row['name'],row['backend']))
        exact=bits(a['sandbox_'+key+'_states'],b['sandbox_'+key+'_states']) and bits(a['sandbox_'+key+'_times'],b['sandbox_'+key+'_times'])
        branch_name=key+'-branch.json'
        branch_exact=(WORK/'run-current'/branch_name).read_bytes()==(WORK/'run-accepted032'/branch_name).read_bytes()
        edited.append(dict(**row,accepted032_trace_bitwise=exact,accepted032_branch_exact=branch_exact,
            accepted032_checks_passed=old_row['checks_passed']))
        gates['sandbox_'+key]=bool(row['checks_passed'] and row['file_continue_exact'] and
            row['file_branch_roundtrip'] and row['parent_file_preserved'] and exact and branch_exact and old_row['checks_passed'])
    gates['annual_file_restart']=all(current['jobs'][x+'_strict20']['checkpoint_continue_exact'] for x in ('python','rust'))
    sources={**current['source_sha256'],**ref['source_sha256'],**loaded_sources(ROOT),
        'scripts/assess_current_runtime375.py':sha(__file__),
        'scripts/validation/eih_scalar.rs':sha(ROOT/'scripts/validation/eih_scalar.rs'),
        'scripts/independent_eih_rust.py':sha(ROOT/'scripts/independent_eih_rust.py')}
    for name in ('pyproject.toml','rust/solar_core/Cargo.toml','rust/solar_core/Cargo.lock',
                 'rust/solar_native/Cargo.toml','rust/solar_native/Cargo.lock','rust/solar_native/pyproject.toml'):
        sources[name]=sha(ROOT/name)
    if any(sha(ROOT/name)!=expected for name,expected in sources.items()):
        raise ValueError('Scientific source changed after execution375')
    with (ROOT/ARRAYS).open('xb') as stream:
        np.savez_compressed(stream,**data)
    output=dict(stage=375,protocol=PROTOCOL,protocol_sha256=PROTOCOL_SHA,
        runtime_commit=p['runtime_commit'],accepted_commit=p['accepted_commit'],units='SI',origin=p['origin'],
        settings=p['settings'],epochs_jd_tdb=p['epochs_jd_tdb'],holdout_times_seconds=p['holdout_times_seconds'],
        source_sha256=sources,environment=current['environment'],
        input_sha256={name:expected for name,expected in p['input_sha256'].items() if not name.startswith('.tools/')},
        historical_cache_sha256={name:expected for name,expected in p['input_sha256'].items() if name.startswith('.tools/')},
        raw_jpl_sha256=p['raw_jpl_sha256'],raw_jpl_responses_verified=40,initial_jpl_overlap=overlap,
        array_archive=ARRAYS,array_sha256=sha(ROOT/ARRAYS),results=results,sensitivity=sensitivity_rows,
        regression=regression,stored141=stored,sandbox=edited,reference=ref,
        executed_jobs=current['jobs'],accepted032_jobs=old['jobs'],gates=gates,
        solver_executed=True,current_runtime_qualified=all(gates.values()),
        failed_criteria=[name for name,passed in gates.items() if not passed],
        original_failure_retained=True,jpl_new_epochs_checked=False,
        historical_reports_unchanged=True,physical_model_changed=False,
        timings_note='Jobs overlapped on one host; includes diagnostics/recording/checkpoint controls; not a performance comparison.',
        limitations=p['limitations'])
    write_json(ROOT/REPORT,output)
    print(json.dumps(dict(qualified=output['current_runtime_qualified'],failed=output['failed_criteria'],
        earth_moon={k:v['earth_moon'] for k,v in results.items()},sensitivity=sensitivity_rows),indent=2),flush=True)
    return output['current_runtime_qualified']


if __name__=='__main__':
    sys.exit(0 if assess() else 1)
