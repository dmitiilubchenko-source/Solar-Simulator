"""Current040 fresh-year v1. Preflight is not propagation or scientific acceptance.

Historical recompute/replay and their manifests are immutable separate objects.
The caller must authenticate the published ZIP and supply its manifest pin.
"""
import argparse
import hashlib
from importlib import metadata, util
import json
from pathlib import Path
import sys
import sysconfig
import traceback

COMMIT='237f73612c3c159acf92b32a15cf0289958fd921'
TREE='5cf43fd9c5bb7d0d80a427d8a6d11ec8b81cb8e9'
NATIVE='a2b7e07573720a269efc712ee4fb74dcc747d24a4967d72d4c3d812158b3399b'
WHEEL='5c2db314218484f5cb8b436de4479d5ecb069b56a5bd621eaa6e5cd5c70a5adb'

def require(ok,message):
    if not ok:raise ValueError(message)

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def checked_file(root,name,digest):
    path=root/name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts and
            path.resolve().is_relative_to(root) and not any(p.is_symlink() for p in (path,*path.parents)),
            'Unsafe binding path: '+name)
    require(path.is_file() and sha(path)==digest,'Bound file mismatch: '+name)

def preflight(root,pin):
    root=Path(root).resolve();manifest=root/'verification-current040/manifest-v1.json'
    require(pin and sha(manifest)==pin,'Current manifest SHA mismatch')
    m=json.loads(manifest.read_bytes())
    require(m['kind']=='current040-fresh-year-v1' and m['scientific_execution_completed'] is False,
            'Not a current preflight manifest')
    require((m['source_commit'],m['source_tree'])==(COMMIT,TREE),'Wrong source object')
    require(m['native_SHA256']==NATIVE and m['wheel_SHA256']==WHEEL,'Wrong native lineage')
    require(sys.flags.isolated==1 and Path(sys.prefix).resolve()==root/'runtime' and
            Path(sys.executable).resolve()==root/'runtime/python.exe','Packaged isolated Python required')
    require(sysconfig.get_config_var('SOABI')==m['SOABI'] and
            bool(sysconfig.get_config_var('Py_GIL_DISABLED'))==m['free_threaded'],'Wrong Python ABI')
    require(sha(sys.executable)==m['interpreter_SHA256'],'Wrong interpreter')
    actual={p.relative_to(root/'runtime').as_posix() for p in (root/'runtime').rglob('*') if p.is_file()}
    require(actual==set(m['runtime_files']),'Runtime file closure changed')
    for n,h in m['runtime_files'].items():checked_file(root,'runtime/'+n,h)
    for n,h in m['historical_files'].items():checked_file(root,'verification/'+n,h)
    checked_file(root,'verification-current040/recompute_current040_v1.py',m['verifier_SHA256'])
    for name,version in m['distributions'].items():require(metadata.version(name)==version,'Distribution version: '+name)
    require(metadata.version('solar-native')==metadata.version('solar-simulator')=='0.4.0','Wrong Solar version')
    import solar_simulator,solar_native,numpy,scipy
    for module in (solar_simulator,solar_native,numpy,scipy):
        require(Path(module.__file__).resolve().is_relative_to(root/'runtime'),'External module import')
    require(sha(getattr(solar_native,'solar_native',solar_native).__file__)==NATIVE,'Wrong native binary')
    bundle=root/'verification'
    spec=util.spec_from_file_location('historical_replay_v1',bundle/'replay_jpl.py')
    checker=util.module_from_spec(spec);spec.loader.exec_module(checker)
    replay=checker.replay(bundle)  # Offline old evidence, never current certification.
    require(replay['checks_passed'],'Historical saved replay failed')
    require(sha(bundle/'initial.json')==m['initial_SHA256'] and
            sha(bundle/'reference.json')==m['reference_SHA256'],'IC/reference mismatch')
    initial=json.loads((bundle/'initial.json').read_bytes());ref=json.loads((bundle/'reference.json').read_bytes())
    require(initial['settings']==m['settings'] and initial['origin']==m['origin'],'Settings/frame mismatch')
    require(initial['units']==m['units']=='SI' and ref['epochs_jd_tdb']==m['epochs_jd_tdb'],'Units/epochs mismatch')
    require(len(m['epochs_jd_tdb'])==125 and m['packet_steps']==20,'Wrong sampling/packet contract')
    return m,checker

def propagate(root,pin,output):
    """No cached-array input or injected solver. Persist real states before assessment."""
    root=Path(root).resolve();output=Path(output).resolve()
    require(not output.is_relative_to(root),'Raw output must be outside sealed package')
    output.mkdir(parents=True,exist_ok=False)
    result={'status':'STARTED','solver_executed':False,'samples':0,'packets':0,'scientific_PASS':False,'checks_passed':False}
    try:
        m,checker=preflight(root,pin)
        import numpy as np
        from solar_simulator.storage import load
        from solar_simulator.time_control import advance_towards
        from solar_simulator.diagnostics import model_invariants
        bundle=root/'verification';state=load(bundle/'initial.json');settings=state.settings
        ref=json.loads((bundle/'reference.json').read_bytes());stored=np.asarray(json.loads((bundle/'trajectories.json').read_bytes())['profiles']['rust_tighter'])
        times=(np.array(m['epochs_jd_tdb'])-state.origin.epoch_jd_tdb)*86400
        energy0,_,_=model_invariants(state.initial,settings.physics,settings.figures)
        values=[];energy_residual=0.
        with (output/'states.jsonl').open('x',encoding='utf8') as stream:
            for target in times:
                while state.time<target:
                    before=state;state=advance_towards(state,float(target),20)
                    result['solver_executed']=True;result['packets']+=1
                    require(state is not before and state.time>before.time,'No real state advance')
                    require(state.settings==settings and not state.halted,'Unexpected settings/stop')
                require(state.time==target,'Wrong output epoch')
                row=[[b.position.x,b.position.y,b.position.z,b.velocity.x,b.velocity.y,b.velocity.z] for b in state.bodies]
                stream.write(json.dumps({'time':state.time,'states':row},allow_nan=False)+'\n');stream.flush()
                values.append(row);result['samples']=len(values)
                energy,_,_=model_invariants(state.bodies,settings.physics,settings.figures)
                energy_residual=max(energy_residual,abs(energy-energy0)/abs(energy0))
        actual=np.array(values);np.savez(output/'propagated.npz',states=actual,times=times)
        expected=np.array([[x['position']+x['velocity'] for x in b['states']] for b in ref['bodies']]).transpose(1,0,2)
        rows={}
        for i,name in enumerate(checker.NAMES):
            jpl,_=checker.maximum_error(actual[:,i],expected[:,i]);old,_=checker.maximum_error(actual[:,i],stored[:,i])
            rows[name]=dict(jpl_residual=jpl,stored_difference=old)
        lunar,_=checker.maximum_error(actual[:,4]-actual[:,3],expected[:,4]-expected[:,3])
        old_lunar,_=checker.maximum_error(actual[:,4]-actual[:,3],stored[:,4]-stored[:,3])
        physical=all(r['jpl_residual']['position_metres']<10000 for r in rows.values()) and lunar['position_metres']<1000
        reproduction=all(r['stored_difference']['position_metres']<.1 and r['stored_difference']['velocity_m_per_s']<1e-5 for r in rows.values()) and old_lunar['position_metres']<.1 and old_lunar['velocity_m_per_s']<1e-5
        result.update(status='COMPLETE',results=rows,moon_relative_jpl=lunar,moon_relative_stored_difference=old_lunar,
                      energy_residual=energy_residual,physical_goals_passed=physical,stored_reproduction_passed=reproduction,
                      scientific_PASS=physical and reproduction,checks_passed=physical and reproduction,duration_seconds=state.time,manifest_SHA256=pin)
    except BaseException as exc:
        result.update(status='FAILED',error_type=type(exc).__name__,error=str(exc))
        (output/'failure.txt').write_text(traceback.format_exc(),encoding='utf8')
        raise
    finally:
        with (output/'result.json').open('x',encoding='utf8') as f:json.dump(result,f,indent=2,allow_nan=False);f.write('\n')
    require(result['scientific_PASS'],'Fresh scientific criteria failed; raw/report preserved')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path)
    p.add_argument('--manifest-sha256',required=True);p.add_argument('--run',action='store_true')
    p.add_argument('--output',type=Path);a=p.parse_args()
    if a.run:
        require(a.output is not None,'Explicit new raw output directory required')
        result=propagate(a.root,a.manifest_sha256,a.output)
    else:
        preflight(a.root,a.manifest_sha256)
        result=dict(status='PREFLIGHT_ONLY',scientific_execution_completed=False,scientific_PASS=False)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
