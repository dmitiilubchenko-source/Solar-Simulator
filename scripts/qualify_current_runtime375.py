"""Scoped, preregistered qualification375; never overwrite historical evidence."""
import argparse
from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'scripts/current-runtime-375-protocol.json'
PROTOCOL_SHA = 'd50dbc891ca79c7f9783e316234248f2fd856866fd8923a7a5888fc23f924dfb'
WORK = ROOT/'.tools/qualification375'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def protocol(path=None, expected_sha=None):
    path = Path(path) if path is not None else ROOT/PROTOCOL
    if path.resolve() != (ROOT/PROTOCOL).resolve() and expected_sha is None:
        raise ValueError('Explicit protocol SHA256 required')
    if sha(ROOT/PROTOCOL) != PROTOCOL_SHA:
        raise ValueError('Changed preregistered protocol375')
    original = json.loads((ROOT/PROTOCOL).read_bytes())
    if sha(path) != (expected_sha or PROTOCOL_SHA):
        raise ValueError('Changed protocol SHA256')
    value = json.loads(path.read_bytes())
    # Only new execution provenance may vary. No new scientific protocol.
    mutable = {'runtime_commit', 'candidate_native', 'candidate_environment'}
    if {k:v for k,v in value.items() if k not in mutable} != {k:v for k,v in original.items() if k not in mutable}:
        raise ValueError('Changed scientific contract375')
    return value


def verify_inputs(p, root=ROOT):
    for name, expected in {**p['input_sha256'], **p['raw_jpl_sha256']}.items():
        if sha(Path(root)/name) != expected:
            raise ValueError('Changed qualification input: '+name)


def job_folder(work, version):
    folder = Path(work)/('run-'+version)
    folder.mkdir(parents=True, exist_ok=False)
    return folder


def activate(runtime):
    if any(n.startswith('solar_simulator') for n in sys.modules):
        raise RuntimeError('Select runtime before importing any physical modules')
    sys.path[:0] = [str(runtime/'src'), str(ROOT)]
    import solar_simulator
    if not Path(solar_simulator.__file__).resolve().is_relative_to(runtime.resolve()):
        raise RuntimeError('Wrong runtime imported')


def snapshot(runtime):
    """Freeze complete runtime/data plus the scientific drivers for this job."""
    paths = list((runtime/'src/solar_simulator').rglob('*.py'))
    paths += list((runtime/'src/solar_simulator/data').glob('*'))
    paths += list((ROOT/'rust/solar_core/src').rglob('*.rs'))
    paths += list((ROOT/'rust/solar_native/src').rglob('*.rs'))
    paths += list((ROOT/'scripts').glob('*.py'))
    return {str(p.resolve()):sha(p) for p in paths if p.is_file()}


def unchanged(before):
    if any(not Path(p).is_file() or sha(p) != expected for p,expected in before.items()):
        raise RuntimeError('Sources changed during scientific job')


def environment():
    from solar_simulator.recipe import runtime_fingerprint
    value = runtime_fingerprint('rust')
    value.pop('package_files')
    return value


def sources(runtime):
    """Imported compute/provenance modules, Rust sources and immutable data."""
    result = {}
    package = (runtime/'src/solar_simulator').resolve()
    for module in list(sys.modules.values()):
        name = getattr(module, '__file__', None)
        if not name:
            continue
        path = Path(name).resolve()
        if path.suffix == '.py' and path.is_relative_to(package):
            result['src/solar_simulator/'+path.relative_to(package).as_posix()] = sha(path)
        elif path.suffix == '.py' and path.is_relative_to(ROOT/'scripts'):
            result[path.relative_to(ROOT).as_posix()] = sha(path)
    for path in (runtime/'src/solar_simulator/data').glob('*'):
        if path.is_file():
            result['src/solar_simulator/data/'+path.name] = sha(path)
    for directory in ('rust/solar_core/src', 'rust/solar_native/src'):
        for path in (ROOT/directory).rglob('*.rs'):
            result[path.relative_to(ROOT).as_posix()] = sha(path)
    result['scripts/qualify_current_runtime375.py'] = sha(__file__)
    return dict(sorted(result.items()))


def strict_seed(backend):
    from solar_simulator.application_profiles import solar_sandbox
    from solar_simulator.storage import load, to_document
    seed = solar_sandbox(backend=backend)
    seed = replace(seed, settings=replace(seed.settings, rtol=3e-14))
    saved = load(ROOT/'docs/solar-sandbox-strict-checkpoint.json')
    expected = to_document(replace(saved, settings=replace(saved.settings, backend=backend)))
    if to_document(seed) != expected:
        raise ValueError('Current initial state/settings differ from pinned Strict checkpoint')
    return seed


def propagate(times, backend, rtol, packet, label, folder, arrays, resume=False):
    from scripts.assess_sandbox_planets import states
    from solar_simulator.diagnostics import model_invariants
    from solar_simulator.storage import save, load, to_document
    from solar_simulator.time_control import advance_towards
    seed = strict_seed(backend)
    state = replace(seed, settings=replace(seed.settings, rtol=rtol))
    initial_document = to_document(state)
    energy0 = model_invariants(state.initial, state.settings.physics, state.settings.figures)[0]
    settings = state.settings
    values, ends, resumed_values = [], [], []
    drift = 0.
    restored = None
    start = perf_counter()
    for index,target in enumerate(times):
        while state.time < target:
            previous = state.time
            state = advance_towards(state, float(target), packet)
            ends.append([previous,state.time])
        if state.time != target or state.halted or state.settings != settings:
            raise ValueError('Changed profile/epoch or incomplete propagation')
        values.append(states(state.bodies))
        energy = model_invariants(state.bodies, settings.physics, settings.figures)[0]
        drift = max(drift, abs(energy-energy0)/abs(energy0))
        if restored is not None:
            while restored.time < target:
                restored = advance_towards(restored, float(target), packet)
            if to_document(restored) != to_document(state):
                raise ValueError('Fresh file checkpoint continuation differs')
            resumed_values.append(states(restored.bodies))
        if resume and index == len(times)//2:
            file = folder/(label+'-middle.json')
            save(state,file)
            restored = load(file)
            if to_document(restored) != to_document(state):
                raise ValueError('Middle checkpoint codec differs')
            resumed_values.append(states(restored.bodies))
    if to_document(seed) != to_document(strict_seed(backend)):
        raise ValueError('Initial parent changed')
    arrays[label+'_values'] = np.asarray(values)
    arrays[label+'_packets'] = np.asarray(ends)
    if resume:
        arrays[label+'_resumed_values'] = np.asarray(resumed_values)
    final = json.dumps(to_document(state),sort_keys=True,separators=(',',':'),allow_nan=False)
    arrays[label+'_final_document'] = np.asarray(final)
    return dict(seconds=perf_counter()-start, packets=len(ends), rtol=rtol,
        packet_max_steps=packet, settings=json.loads(json.dumps(asdict(settings))),
        relative_energy_residual=drift, exact_times=True, settings_preserved=True,
        initial_parent_preserved=True, checkpoint_continue_exact=True if resume else None,
        initial_document=initial_document)


def sandbox_jobs(folder, arrays, native_calls, p=None):
    import scripts.assess_sandbox_limits as limits
    from solar_simulator.sandbox import save_branch, load_branch, to_branch_document
    from solar_simulator.storage import save, load, to_document
    original = limits.advance_towards
    results = []
    for backend in ('python','rust'):
        for name in (p or protocol())['jobs']['sandbox']:
            label = backend+'_'+name
            trace, clocks, last = [], [], []
            def recorded(state, target, *args):
                result = original(state,target,*args)
                trace.append(np.concatenate(limits.arrays(result.bodies)[:2],axis=1))
                clocks.append(result.time)
                last[:] = [result]
                return result
            limits.advance_towards = recorded
            count = native_calls[0]
            try:
                row = limits.assess(name,backend)
            finally:
                limits.advance_towards = original
            parent,branch = limits.scenario(name,backend)
            parent_before = to_document(parent)
            branch_before = to_branch_document(branch)
            path = folder/(label+'-branch.json')
            save_branch(branch,path)
            if to_branch_document(load_branch(path)) != branch_before:
                raise ValueError('Sandbox file branch roundtrip differs')
            final = last[0]
            path = folder/(label+'-final.json')
            save(final,path)
            loaded = load(path)
            target = final.time+final.settings.dt
            if to_document(original(loaded,target)) != to_document(original(final,target)):
                raise ValueError('Sandbox file continuation differs')
            if to_document(parent) != parent_before or to_branch_document(branch) != branch_before:
                raise ValueError('Sandbox original parent changed')
            row.update(file_branch_roundtrip=True,file_continue_exact=True,parent_file_preserved=True)
            row['native_force_calls'] = native_calls[0]-count
            if (backend=='rust') != (row['native_force_calls']>0):
                raise ValueError('Sandbox backend force execution differs')
            arrays['sandbox_'+label+'_states'] = np.asarray(trace)
            arrays['sandbox_'+label+'_times'] = np.asarray(clocks)
            results.append(row)
            print('sandbox',label,row['checks_passed'],flush=True)
    return results


def runtime_job(version, *, work=WORK, protocol_path=None, expected_sha=None):
    p = protocol(protocol_path, expected_sha)
    verify_inputs(p)
    runtime = ROOT if version == 'current' else Path(work)/'accepted032'
    folder = job_folder(work, version)
    activate(runtime)
    from solar_simulator import native_forces
    from solar_simulator.ephemerides import solar_system
    from scripts.assess_sandbox_planets import states
    from scripts.assess_sandbox_models import load_inputs
    from scripts.native_audit import require_native
    print(require_native(),flush=True)
    before = snapshot(runtime)
    env = environment()
    import solar_native
    compiled = getattr(solar_native,'solar_native',solar_native)
    native = p.get('candidate_native', p['native032']) if version == 'current' else p['native032']
    if sha(compiled.__file__) != native['sha256']:
        raise ValueError('Native binary differs from accepted032 comparison binary')
    if version == 'current' and 'candidate_environment' in p and env != p['candidate_environment']:
        raise ValueError('Candidate environment changed')
    initial,origin,_,_,_ = load_inputs()
    if asdict(origin) != p['origin']:
        raise ValueError('Origin differs from protocol')
    native_calls = [0]
    prepare = native_forces.prepare
    def counted_prepare(*args,**kwargs):
        force = prepare(*args,**kwargs)
        def counted(*a,**k):
            native_calls[0] += 1
            return force(*a,**k)
        return counted
    native_forces.prepare = counted_prepare
    times = (np.asarray(p['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400
    holdout = np.asarray(p['holdout_times_seconds'])
    arrays = dict(times=times,holdout_times=holdout,initial=states(initial),
        masses=np.array([b.mass for b in initial]))
    jobs = {}
    for backend in ('python','rust'):
        variants = [('strict20',3e-14,20)]
        if version == 'current':
            variants += [('standard20',1e-13,20),('strict10',3e-14,10)]
        for name,rtol,packet in variants:
            key = backend+'_'+name
            count = native_calls[0]
            jobs[key] = propagate(times,backend,rtol,packet,key,folder,arrays,
                resume=(version=='current' and name=='strict20'))
            jobs[key]['native_force_calls'] = native_calls[0]-count
            if (backend=='rust') != (jobs[key]['native_force_calls']>0):
                raise ValueError('Backend force execution does not match declared backend')
            print(version,key,jobs[key]['seconds'],flush=True)
            with (folder/(key+'-outputs.npz')).open('xb') as stream:
                np.savez_compressed(stream,**arrays)
            write_json(folder/(key+'-receipt.json'),jobs[key])
        key = backend+'_holdout20'
        count = native_calls[0]
        jobs[key] = propagate(holdout,backend,3e-14,20,key,folder,arrays)
        jobs[key]['native_force_calls'] = native_calls[0]-count
        if (backend=='rust') != (jobs[key]['native_force_calls']>0):
            raise ValueError('Holdout backend force execution differs')
    edited = sandbox_jobs(folder,arrays,native_calls,p)
    if environment() != env:
        raise RuntimeError('Numerical environment changed during job')
    unchanged(before)
    with (folder/'outputs.npz').open('xb') as stream:
        np.savez_compressed(stream,**arrays)
    write_json(folder/'receipt.json',dict(version=version,
        runtime_commit=p['runtime_commit'] if version=='current' else p['accepted_commit'],
        driver_sha256=sha(__file__),protocol_sha256=sha(protocol_path or ROOT/PROTOCOL),
        runtime_source_root=str(runtime.relative_to(ROOT)) if runtime!=ROOT else '.',
        solver_executed=True,environment=env,source_sha256=sources(runtime),
        outputs_sha256=sha(folder/'outputs.npz'),jobs=jobs,sandbox=edited,
        total_native_force_calls=native_calls[0]))


def reference_job(*, work=WORK, protocol_path=None, expected_sha=None):
    p = protocol(protocol_path, expected_sha)
    verify_inputs(p)
    folder = job_folder(work, 'reference')
    activate(ROOT)
    before = snapshot(ROOT)
    from scripts.assess_sandbox_models import load_inputs,figure_reference
    from scripts.assess_relative_coordinates import independent_reference
    initial,origin,_,_,_ = load_inputs()
    # Exact existing loader in a fresh directory forces a fresh compilation.
    oracle_root = folder/'oracle'
    script = oracle_root/'scripts/independent_eih_rust.py'
    scalar = oracle_root/'scripts/validation/eih_scalar.rs'
    scalar.parent.mkdir(parents=True)
    script.write_bytes((ROOT/'scripts/independent_eih_rust.py').read_bytes())
    scalar.write_bytes((ROOT/'scripts/validation/eih_scalar.rs').read_bytes())
    spec = importlib.util.spec_from_file_location('_oracle375',script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    oracle = module.load_oracle()
    library = oracle_root/'.tools'/('independent-eih-'+oracle.source_sha256[:16]+'.dll')
    data,rows = {},{}
    for name,times in [('annual',(np.asarray(p['epochs_jd_tdb'])-origin.epoch_jd_tdb)*86400),
                       ('holdout',np.asarray(p['holdout_times_seconds']))]:
        # independent_reference prefixes .tools; an absolute target overrides it.
        # The new run-reference directory is exclusive, so no old cache is reused.
        cache = str((folder/name).resolve())
        start = perf_counter()
        value,convergence = independent_reference(initial,strict_seed('python').settings.figures,
            times,levels=tuple(map(tuple,p['independent_reference']['levels'])),
            cache_name=cache,acceleration_function=oracle,figure_acceleration_function=figure_reference)
        data[name+'_values'] = value
        rows[name] = dict(convergence=convergence,seconds=perf_counter()-start,
            output_sha256=sha(ROOT/'.tools'/(cache+'.npz')))
    unchanged(before)
    write_json(folder/'receipt.json',dict(solver_executed=True,protocol_sha256=sha(protocol_path or ROOT/PROTOCOL),
        oracle_source_sha256=oracle.source_sha256,oracle_binary_sha256=sha(library),
        oracle_compiler=oracle.compiler_version,loader_sha256=sha(script),
        source_sha256=sources(ROOT),results=rows,environment=environment()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job',choices=('current','accepted032','reference'))
    parser.add_argument('--work', type=Path, default=WORK)
    parser.add_argument('--protocol', type=Path)
    parser.add_argument('--protocol-sha256')
    args = parser.parse_args()
    options = dict(work=args.work.resolve(), protocol_path=args.protocol, expected_sha=args.protocol_sha256)
    if args.job == 'reference':
        reference_job(**options)
    else:
        runtime_job(args.job, **options)


if __name__ == '__main__':
    main()
