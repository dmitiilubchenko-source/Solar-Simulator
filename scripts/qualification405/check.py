"""Bounded text-only source/UI check. Reuses the 403 guard and 404 recorder."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R))
from scripts import q2_execution398 as q
from scripts.q2_text_delta403 import compare

WARNING_PATH = 'src/solar_simulator/inspection.py'


def require_inventory(old, new):
    if old.keys() != new.keys() or {k for k in old if old[k] != new[k]} != {WARNING_PATH}:
        raise ValueError('Expected exactly one existing inspection.py change')


def blob_sha256(root, inventory):
    """Hash every exact Git blob, including files omitted by sparse checkout."""
    objects = sorted({meta.split()[2] for meta in inventory.values()})
    data = subprocess.check_output(['git','-C',str(root),'cat-file','--batch'],
                                   input=('\n'.join(objects)+'\n').encode())
    offset = 0; hashes = {}
    for oid in objects:
        end = data.index(b'\n',offset); header = data[offset:end].split()
        assert header[0].decode() == oid and header[1] == b'blob'
        size = int(header[2]); start = end+1
        hashes[oid] = hashlib.sha256(data[start:start+size]).hexdigest()
        assert data[start+size:start+size+1] == b'\n'
        offset = start+size+1
    assert offset == len(data)
    return {name:hashes[meta.split()[2]] for name,meta in inventory.items()}


def source_audit(plan):
    root, base = Path(plan['candidate_source']), Path(plan['base_source'])
    def git(*args):
        return subprocess.check_output(['git', '-C', str(root), *args])
    assert git('rev-parse', 'HEAD').decode().strip() == plan['candidate_commit']
    assert git('rev-parse', 'HEAD^').decode().strip() == plan['base_commit']
    assert git('rev-parse', 'HEAD^{tree}').decode().strip() == plan['candidate_tree']
    assert not git('status', '--porcelain')
    assert subprocess.check_output(['git', '-C', str(base), 'rev-parse', 'HEAD']).decode().strip() == plan['base_commit']
    assert not subprocess.check_output(['git', '-C', str(base), 'status', '--porcelain'])
    def inventory(commit):
        return {name.decode(): meta.decode() for row in git('ls-tree', '-r', '-z', commit).split(b'\0') if row
                for meta, name in [row.split(b'\t', 1)]}
    old, new = inventory(plan['base_commit']), inventory(plan['candidate_commit'])
    require_inventory(old, new)
    before, after = (base / WARNING_PATH).read_bytes(), (root / WARNING_PATH).read_bytes()
    assert before == git('show', plan['base_commit'] + ':' + WARNING_PATH)
    assert after == git('show', plan['candidate_commit'] + ':' + WARNING_PATH)
    delta = compare(before, after)
    assert delta['old_text'].count(plan['old_sentence']) == 1
    assert delta['new_text'] == delta['old_text'].replace(plan['old_sentence'], plan['new_sentence'])
    raw_old = blob_sha256(base, old)
    raw_new = blob_sha256(root, new)
    require_inventory(raw_old, raw_new)
    # Source imports need actual file provenance as well as Git-object identity.
    actual_old = {name:q.sha(base/name) for name in old if (base/name).is_file()}
    actual_new = {name:q.sha(root/name) for name in new if (root/name).is_file()}
    common = actual_old.keys() & actual_new.keys()
    assert {name for name in common if actual_old[name] != actual_new[name]} == {WARNING_PATH}
    runtime = {name for name in old if name.startswith(('src/','rust/'))}
    assert runtime <= common
    return dict(delta=delta, Git_blobs_before=old, Git_blobs_after=new,
                Git_blob_SHA256_before=raw_old, Git_blob_SHA256_after=raw_new,
                working_SHA256_before=actual_old, working_SHA256_after=actual_new,
                absent_from_base_checkout=sorted(old.keys()-actual_old.keys()),
                absent_from_new_checkout=sorted(new.keys()-actual_new.keys()),
                diff=git('diff', plan['base_commit'], plan['candidate_commit']).decode(),
                unchanged_file_count=len(old)-1, candidate_tree=plan['candidate_tree'])


def main():
    from contextlib import ExitStack
    from copy import deepcopy
    from unittest.mock import patch
    from scripts.q2_source_adapter396 import require_origins
    from scripts.qualification404.check_gui import Recorder
    W = R / '.tools/qualification405-20261109'
    plan = json.loads((R / 'scripts/qualification405/plan.json').read_bytes())
    for name, digest in plan['input_SHA256'].items():
        q.require_sha(R / name, digest)
    source = source_audit(plan)
    q.atomic_json(W/'source-audit.json',source)
    sys.path.insert(0, str(Path(plan['candidate_source']) / 'src'))
    import tkinter as tk
    import solar_simulator, solar_native, numpy, scipy, matplotlib
    from solar_simulator import recipe, inspection, inspection_view, application_profiles
    from solar_simulator import storage, experiment, accuracy, nbody_rotation, app
    require_origins(solar_simulator.__file__, [numpy.__file__, scipy.__file__, solar_native.__file__],
                    plan['candidate_source'], sys.prefix, Path(plan['interpreter']).parents[1])
    native = Path(getattr(solar_native, 'solar_native', solar_native).__file__)
    q.require_sha(native, plan['native_SHA256'])
    fp = recipe.runtime_fingerprint('rust')
    baseline = json.loads((R / '.tools/qualification404-20261108/new-actual-environment.json').read_bytes())
    assert {k:v for k,v in fp.items() if k != 'package_files'} == {k:v for k,v in baseline.items() if k != 'package_files'}
    assert {k for k in fp['package_files'].keys() | baseline['package_files'].keys()
            if fp['package_files'].get(k) != baseline['package_files'].get(k)} == {'inspection.py'}
    raw = (json.dumps(fp, indent=2)+'\n').encode()
    digest = hashlib.sha256(raw).hexdigest()
    assert digest != plan['base_fingerprint']
    profile_path = W/'new-actual-environment.json'
    if profile_path.exists():
        assert profile_path.read_bytes() == raw  # Retain completed prior emission.
    else:
        with profile_path.open('xb') as f:f.write(raw)
    calls = []
    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError('No integration/RHS in warning qualification405')
    states = [('zero', application_profiles.scenario('sun-earth')),
              ('one', application_profiles.lunar_rotation()), ('two', application_profiles.two_q2_demo())]
    doc = deepcopy(storage.to_document(states[-1][1]))
    names = {'A':'Custom', 'B':'Other'}
    for field in ('bodies', 'initial'):
        for item in doc[field]:
            item['name'] = names[item['name']]
        doc[field][0]['position'][0] += 123.
    for field in ('rotations', 'initial_rotations'):
        for item in doc[field]:
            item['body'] = names[item['body']]
    doc['settings']['relative_pair'] = ['Custom','Other']
    custom_file = W / 'arbitrary-two.json'
    if custom_file.exists():
        assert json.loads(custom_file.read_bytes()) == doc
    else:q.atomic_json(custom_file, doc)
    states.append(('arbitrary_loaded_two', storage.load(custom_file)))
    checkpoint_sha = q.sha(custom_file)
    rec = Recorder(); rec.name = 'single_root_text_smoke405'
    variants = []; numeric_reports = {}; lab = None; view = None
    with ExitStack() as stack:
        for module, name in [(app,'advance'), (experiment,'advance'), (nbody_rotation,'integrate'),
                             (nbody_rotation,'solve_ivp'), (accuracy,'evolve_accurate'),
                             (solar_native,'point_acceleration')]:
            stack.enter_context(patch.object(module, name, forbidden))
        stack.enter_context(rec.instrument(tk, app.Laboratory))
        root = tk.Tk(); root.withdraw(); rec.attach(root)
        versions = dict(Tcl=str(root.tk.call('info','patchlevel')), Tk=str(root.tk.call('set','tk_patchLevel')))
        try:
            lab = app.Laboratory(root, states[0][1])
            warning = inspection.TWO_Q2_EXPERIMENTAL_WARNING
            for name, state in states:
                before = storage.to_document(state); count = len(state.rotations)
                numeric = inspection.cli.report(state); report = inspection.report(state)
                lab._set_experiment(state)
                payload = inspection_view.prepare_inspection(before, lambda:False, lambda *a:None)
                # The warning itself is pure presentation. Existing full diagnostics
                # still evaluate their normal invariant/potential routines, not RHS.
                with patch.object(nbody_rotation, 'corrections', forbidden), patch.object(nbody_rotation, 'invariants', forbidden):
                    assert bool(inspection.experimental_q2_warning(state.rotations)) == (count == 2)
                    assert (warning in inspection_view.rotation_text(payload)) == (count == 2)
                assert (warning in lab.model_info.get()) == (count == 2)
                detail = report['numerical_reliability']
                assert detail['qualification']['current_trajectory_certified'] is False
                assert detail['accuracy']['global_position_error_metres'] is None
                assert detail['accuracy']['global_velocity_error_m_per_s'] is None
                assert {k:v for k,v in report.items() if k != 'numerical_reliability'} == numeric
                if count == 2:
                    view = lab._show_inspection()
                    rec.until(root,lambda:view.viewer is not None)
                    assert all(warning in field.get('1.0','end') for field in view.texts)
                    view.close(); view = None
                assert storage.to_document(state) == before
                variants.append(dict(id=name,figures=count,warning_present=count==2,
                    current_trajectory_certified=False,global_error_bound=None,
                    q_S_settings_unchanged=True,model_info_inspector_consistent=True))
                numeric_reports[name] = numeric
                q.atomic_json(W/(name+'-verified.json'),dict(variant=variants[-1],
                    source_commit=plan['candidate_commit'],checkpoint=before,numerical_report=numeric))
            assert q.sha(custom_file) == checkpoint_sha and not calls
            for token in plan['required_text_tokens']:
                assert token in warning, token
            assert plan['old_sentence'] not in warning
            lab.close(); lab = None
            rec.pump(root)
            assert not rec.errors and not rec.queue(root) and not rec.foreign_cancellations
        finally:
            if view is not None:view.close()
            if lab is not None:lab.close()
        assert recipe.runtime_fingerprint('rust') == fp
    q.atomic_json(W/'checks.json',dict(status='PASS_TARGETED_TEXT_SOURCE_GUI405',source=source,
        source_commit=plan['candidate_commit'],actual_source_fingerprint=digest,
        actual_import=solar_simulator.__file__,dependency_prefix=sys.prefix,native=str(native),
        native_SHA256=q.sha(native),versions=dict(Python=sys.version,NumPy=numpy.__version__,
        SciPy=scipy.__version__,Matplotlib=matplotlib.__version__,**versions),
        variants=variants,numerical_reports=numeric_reports,checkpoint_SHA256=checkpoint_sha,
        evolution_calls=len(calls),callbacks=rec.events,destroy=rec.destroys,
        background_errors=rec.errors,orbits=0,scope='One literal delta only; original399-404 evidence remains historical, no source-bound receipt transfer.'))
    print('PASS one literal/full Git/AST/SHA;4 UI states;1 retained-root close smoke;0 evolution; fingerprint '+digest,flush=True)


if __name__ == '__main__':
    main()
