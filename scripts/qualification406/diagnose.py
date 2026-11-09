"""Small reproductions of the original acceptance failures; no product edits."""
import hashlib
import importlib.util
import json
from pathlib import Path
import runpy
import subprocess
import sys
import traceback

R=Path(__file__).resolve().parents[2];W=R/'.tools/acceptance406-20261109'
P=json.loads((R/'scripts/qualification406/plan.json').read_bytes())
D=W/'diagnostics'


def save(name,value):
    with (D/(name+'.json')).open('x',encoding='utf8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')


def layout(old=False):
    source=Path('C:/Users/Admin/Desktop/Solar-candidate-033-q2-marking-403') if old else Path(P['candidate_source'])
    sys.path.insert(0,str(source/'src'))
    import tkinter as tk
    import solar_simulator
    from solar_simulator.app import Laboratory
    from solar_simulator.application_profiles import lunar_rotation
    assert Path(solar_simulator.__file__).resolve().is_relative_to(source/'src')
    root=tk.Tk();app=Laboratory(root,lunar_rotation());rows=[]
    try:
        state=app.experiment
        for width,height in ((1180,820),(1024,768),(900,720)):
            root.geometry(f'{width}x{height}');root.update()
            for expanded in (False,True):
                if expanded:app._toggle_settings();root.update()
                app.canvas.draw();renderer=app.canvas.get_renderer()
                rows.append(dict(width=width,height=height,settings_open=expanded,
                    actual_root=[root.winfo_width(),root.winfo_height()],
                    canvas_height=app.canvas.get_tk_widget().winfo_height(),
                    expected_canvas_height_greater_than=170,
                    tk_scaling=float(root.tk.call('tk','scaling')),
                    plot_axes_label=list(app.orbit.xaxis.label.get_window_extent(renderer).bounds),
                    lower_title=list(app.energy.title.get_window_extent(renderer).bounds),
                    lower_label=list(app.energy.xaxis.label.get_window_extent(renderer).bounds)))
                assert app.experiment is state
            app._toggle_settings();root.update()
        app.figure.savefig(D/('layout-e9.png' if old else 'layout-405.png'))
    finally:app.close()
    if not old:root.tk.call('update')
    save('layout-e9' if old else 'layout-405',dict(source=str(source),source_import=solar_simulator.__file__,
        app_SHA256=hashlib.sha256((source/'src/solar_simulator/app.py').read_bytes()).hexdigest(),
        rows=rows,failed_canvas_cases=[x for x in rows if x['canvas_height']<=170],
        scope='Layout only; olde9 closing is deliberately not qualified or event-pumped. No orbit calculated.'))


def worker_repro():
    source=Path(P['candidate_source']);sys.path[:0]=[str(source/'src'),str(R)]
    import tkinter as tk
    from solar_simulator import app
    from scripts.qualification404.check_gui import Recorder
    rec=Recorder();rec.name='original_worker_test_reproduction';detail={};failure=None
    target=source/'tests/test_app_workflows.py'
    def trace(frame,event,arg):
        if frame.f_code.co_name=='_check_worker_recovery' and event=='exception' and isinstance(arg[1],AssertionError):
            obj=frame.f_locals.get('app');root=frame.f_locals.get('root')
            detail.update(line=frame.f_lineno,timers_before=frame.f_locals.get('timers_before'),
                actual_queue=rec.queue(root),running=obj.running,future_none=obj.future is None,
                UI_errors=frame.f_locals.get('errors'))
        return trace if frame.f_code.co_name=='_check_worker_recovery' else None
    directory=D/'worker-original';directory.mkdir()
    with rec.instrument(tk,app.Laboratory):
        sys.settrace(trace)
        try:runpy.run_path(str(target))['_check_worker_recovery'](directory)
        except AssertionError:failure=traceback.format_exc()
        finally:sys.settrace(None)
    assert failure and detail['actual_queue'] and detail['line']==121
    save('worker-original',dict(status='ORIGINAL_FAIL_REPRODUCED_NOT_WAIVED',failure=failure,
        failure_locals=detail,callbacks=rec.events,destroy=rec.destroys,background_errors=rec.errors,
        mechanism='The legacy test demands total pending timers grow after manual poll;404 intentionally cancels/replaces its pending poll instead of duplicating it.'))


def poll_contract():
    source=Path(P['candidate_source']);sys.path[:0]=[str(source/'src'),str(R)]
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator import app
    from scripts.qualification404.check_gui import Recorder
    rec=Recorder();rec.name='single_owned_poll_error_contract';errors=[]
    with rec.instrument(tk,app.Laboratory):
        root=tk.Tk();root.withdraw();obj=app.Laboratory(root)
        before=rec.queue(root);obj.batch.set('bad');obj.running=True
        with patch.object(app.messagebox,'showerror',side_effect=lambda *a,**kw:errors.append(a)):obj._poll()
        after=rec.queue(root)
        own=lambda rows:[x['after_id'] for x in rows if x['command'].endswith('_poll')]
        assert len(own(before))==len(own(after))==1 and own(before)!=own(after)
        assert len(errors)==1 and not obj.running and obj.future is None
        rec.pump(root);live=rec.queue(root);assert len(own(live))==1
        obj.close();rec.pump(root);assert not rec.queue(root) and not rec.errors
    save('poll-contract',dict(status='NEW404CONTRACT_CONTROL_PASS_ORIGINAL_TEST_STILL_FAIL',before=before,
        after=after,live=live,callbacks=rec.events,background_errors=rec.errors,
        meaning='One surviving owned40ms poll; previous ID removed; scheduling resumes after error. Does not rewrite or waive original test.'))


def path_control():
    source=Path(P['candidate_source']);sys.path.insert(0,str(source))
    from scripts import build_portable as builder
    external=Path.home()/'Documents/Codex/Solar406-public-path-control-20261109'
    assert not external.exists();external.mkdir()
    inside=D/'private-ancestor';inside.mkdir()
    rows=[];old=builder.ROOT
    seeds=('nbody-rotation.md','rotation-year.md','lunar-spin-initial.md',
           'conservative-rotation.md','harmonic-sphere-validation.md','chart-current-validation.md')
    try:
        for root in (inside,external):
            docs=root/'source/docs';docs.mkdir(parents=True)
            for name in seeds:(docs/name).write_text('',encoding='utf8')
            builder.ROOT=root/'source';error=None;count=None
            try:count=len(builder.copy_public_rotation_documents(root/'output'))
            except ValueError as exc:error=str(exc)
            rows.append(dict(root=str(root),has_private_ancestor='.tools' in docs.parts,
                             error=error,copied_count=count))
    finally:builder.ROOT=old
    assert rows[0]['error'].startswith('Nonpublic portable document') and rows[1]['copied_count']==6
    size=sum(p.stat().st_size for p in external.rglob('*') if p.is_file());assert size<1024**2
    # JPL replay itself passed in the full test; the final privacy assertion
    # inspects absolute ancestor parts. No propagation/replay is repeated here.
    save('path-control',dict(status='PRIVATE_ANCESTOR_SETUP_EFFECT_CONFIRMED',rows=rows,
        external_scratch_bytes=size,external_scratch_cap=1024**2,
        original_failures_remain=True,portable_build_performed=False,
        mechanism='Both document exporter and one JPL bundle test inspect absolute Path.parts, so an otherwise public tree nested below.tools is treated as private.'))


def offline():
    source=Path(P['candidate_source']);data=json.loads((W/'python-results.json').read_bytes());groups={}
    for case in data['nodes']:
        if case['status']=='PASS':continue
        node=case['nodeid'];text=case['trace'] or ''
        if node.startswith('tests/test_app_usability.py'):group='responsive_layout'
        elif node.startswith('tests/test_app_workflows.py'):group='legacy_poll_count_assertion'
        elif case['status']=='ERROR':
            assert 'Exact qualified375 source unavailable:rust/solar_native/Cargo.toml' in text
            group='historical375_cargo_fixture'
        elif node.startswith('tests/test_release_history.py'):group='historical032_cargo_metadata'
        elif node.startswith(('tests/test_portable_rotation_documents.py','tests/test_jpl_replay.py')):group='private_ancestor_setup'
        else:
            assert 'control_row.py' in text,node
            group='historical_control_row_binding'
        groups.setdefault(group,[]).append(case)
    assert {k:len(v) for k,v in groups.items()}==dict(responsive_layout=1,legacy_poll_count_assertion=1,
        historical375_cargo_fixture=10,historical032_cargo_metadata=4,private_ancestor_setup=6,historical_control_row_binding=51)
    spec=importlib.util.spec_from_file_location('exact406history',source/'scripts/release_history.py')
    history=importlib.util.module_from_spec(spec);spec.loader.exec_module(history)
    name='src/solar_simulator/control_row.py'
    old=subprocess.check_output(['git','-C',str(source),'show','e9ddd352:'+name])
    oldsha=hashlib.sha256(old).hexdigest();newsha=hashlib.sha256((source/name).read_bytes()).hexdigest()
    mapped=history.ui_historical_sha(source,name,oldsha)
    assert oldsha!=newsha==mapped
    release=json.loads((source/history.MANIFEST).read_bytes());cargo=[]
    for name in ('rust/solar_core/Cargo.toml','rust/solar_native/Cargo.toml'):
        raw=(source/name).read_bytes().replace(b'\r\n',b'\n');entry=release['files'][name]
        expected=entry['current_sha256'];actual=hashlib.sha256(raw).hexdigest()
        assert actual!=expected
        cargo.append(dict(path=name,actual=actual,expected032=expected,
            source_version033='version = "0.3.3"' in raw.decode()))
    from zipfile import ZipFile
    receipt=json.loads((source/'docs/current-runtime-375-validation.json').read_bytes())
    expected375=receipt['source_sha256']['rust/solar_native/Cargo.toml'];available=[]
    archive_payloads=[]
    for archive_name,digest,names in [(history.QUALIFICATION_ARCHIVE,history.QUALIFICATION_ARCHIVE_SHA,history.QUALIFICATION_FILES),
        (history.LABORATORY_ARCHIVE,history.LABORATORY_ARCHIVE_SHA,history.LABORATORY_FILES),
        (history.ROTATION_ARCHIVE,history.ROTATION_ARCHIVE_SHA,history.ROTATION_FILES)]:
        actual=hashlib.sha256((source/archive_name).read_bytes()).hexdigest();assert actual==digest
        available.append(dict(archive=archive_name,SHA256=actual,includes_native_Cargo='rust/solar_native/Cargo.toml' in names))
        with ZipFile(source/archive_name) as z:
            archive_payloads.append((archive_name,{name:z.read(name) for name in names}))
    assert not any(x['includes_native_Cargo'] for x in available)
    unavailable=[]
    for name,expected in receipt['source_sha256'].items():
        raw=(source/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()==expected:continue
        if any(name in files and hashlib.sha256(files[name]).hexdigest()==expected for _,files in archive_payloads):continue
        dev=R/name
        accepted=subprocess.check_output(['git','-C',str(source),'show',P['accepted032']+':'+name])
        unavailable.append(dict(path=name,expected375=expected,current405=hashlib.sha256(raw).hexdigest(),
            current_dev_bytes_match=dev.is_file() and hashlib.sha256(dev.read_bytes()).hexdigest()==expected,
            accepted032_Git_LF_match=hashlib.sha256(accepted).hexdigest()==expected,
            accepted032_CRLF_representation_match=hashlib.sha256(accepted.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')).hexdigest()==expected))
    save('failure-groups',dict(candidate=P['candidate_commit'],counts={k:len(v) for k,v in groups.items()},
        failures=groups,control_row=dict(old_e9_SHA256=oldsha,current405_SHA256=newsha,history_result=mapped,
        conclusion='Current GUI lifecycle file is correctly rejected by old source receipts; no registered archived old control_row in the current mapping.'),
        cargo=cargo,fixture375=dict(expected_native_Cargo_SHA256=expected375,checked_archives=available,all_unavailable_sources=unavailable,
        conclusion='Exact375fixture does not search an archive containing old Cargo metadata; negative tests are blocked before intended corruption.'),
        caution='First barriers confirmed only. Additional mismatches may be hidden behind them; no old receipt is automatically accepted for current runtime.',
        missing_warning_document=not (source/'docs/q2-application-acceptance-402.md').exists()))


def main():
    D.mkdir(exist_ok=True);mode=sys.argv[1]
    if mode=='all':
        commands=['layout','layout-old','worker-repro','poll-contract','path-control','offline']
        for mode in commands:
            subprocess.run([sys.executable,'-I','-X','utf8','-B',__file__,mode],check=True,cwd=P['candidate_source'])
        print('PASS diagnostic evidence complete; original63FAIL/10ERROR not waived',flush=True)
    elif mode=='layout':layout()
    elif mode=='layout-old':layout(True)
    elif mode=='worker-repro':worker_repro()
    elif mode=='poll-contract':poll_contract()
    elif mode=='path-control':path_control()
    elif mode=='offline':offline()
    else:raise ValueError(mode)


if __name__=='__main__':main()
