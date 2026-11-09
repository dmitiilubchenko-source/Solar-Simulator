"""One bounded real-packet GUI/recovery journey, complementing exact404 receipts."""
from contextlib import ExitStack
import hashlib
import inspect
import json
import math
from pathlib import Path
import sys
from threading import Event
import traceback
from unittest.mock import patch

R=Path(__file__).resolve().parents[2];W=R/'.tools/acceptance406-20261109'
P=json.loads((R/'scripts/qualification406/plan.json').read_bytes())
sys.path[:0]=[str(Path(P['candidate_source'])/'src'),str(R)]
from scripts import q2_execution398 as q
from scripts.qualification404.check_gui import Recorder


def main():
    import tkinter as tk
    from solar_simulator import app as module,storage,experiment,recovery,inspection,recipe
    from solar_simulator.simulation import Body
    from solar_simulator.vector3 import Vector3
    import solar_simulator,solar_native
    assert Path(solar_simulator.__file__).resolve().is_relative_to(Path(P['candidate_source'])/'src')
    assert hashlib.sha256((json.dumps(recipe.runtime_fingerprint('rust'),indent=2)+'\n').encode()).hexdigest()==P['source_fingerprint']
    d=W/'gui';d.mkdir(exist_ok=False)
    q.atomic_json(d/'started.json',dict(candidate=P['candidate_commit'],plan_SHA256=q.sha(W/'gui-plan.json')))
    seed=experiment.create_experiment([Body('probe',1.,Vector3(1,2,3),Vector3(2,-1,.5))],
                                     experiment.Settings(1.,backend='rust',integrator='dop853'))
    rec=Recorder();rec.name='real_packet_dual_window_recovery406'
    entered=Event();release=Event();calls=[];native_calls=[];messages=[];failure=None
    original=module.advance_towards;point=solar_native.point_acceleration
    assert inspect.isbuiltin(point)
    def gated(*args,**kw):
        entered.set()
        if not release.wait(5):raise TimeoutError('Controlled packet gate')
        result=original(*args,**kw);calls.append(dict(time=result.time,backend=result.settings.backend))
        return result
    def native(*args,**kw):
        result=point(*args,**kw);native_calls.append(True);return result
    def analytic(state,t):
        assert state.time==t
        for x,y in zip(state.bodies[0].position.as_list() if hasattr(state.bodies[0].position,'as_list') else
                       [state.bodies[0].position.x,state.bodies[0].position.y,state.bodies[0].position.z],
                       [1+2*t,2-t,3+.5*t]):assert math.isclose(x,y,rel_tol=0,abs_tol=1e-12)
    initial_saved=d/'original-user.json';after_saved=d/'saved-after1.json';two_saved=d/'two-q2-user.json'
    source402=R/'.tools/qualification402-20261108/jobs/main__rust__gui__cold/frame-100.json'
    q.require_sha(source402,json.loads((W/'gui-plan.json').read_bytes())['frame100_SHA256'])
    frame100=json.loads(source402.read_bytes());two_sha=q.sha(source402)
    root=None;a=None;b=None;view=None;checkpoints={};layouts={}
    with ExitStack() as stack:
        stack.enter_context(rec.instrument(tk,module.Laboratory))
        stack.enter_context(patch.object(module,'advance_towards',gated))
        stack.enter_context(patch.object(solar_native,'point_acceleration',native))
        stack.enter_context(patch.object(module.messagebox,'showerror',side_effect=lambda *a,**kw:messages.append(a)))
        try:
            root=tk.Tk();root.withdraw();rec.attach(root)
            wa=tk.Toplevel(root);wa.geometry('1180x820');a=module.Laboratory(wa,seed)
            wb=tk.Toplevel(root);wb.geometry('1180x820');b=module.Laboratory(wb,seed)
            button=lambda obj,text:next(w for w in obj.actions if isinstance(w,tk.ttk.Button) and str(w.cget('text'))==text)
            with patch.object(module.filedialog,'asksaveasfilename',return_value=str(initial_saved)):button(a,'Сохранить JSON').invoke()
            initial_sha=q.sha(initial_saved)
            with patch.object(module.filedialog,'askopenfilename',return_value=''):
                before=storage.to_document(a.experiment);button(a,'Открыть JSON').invoke();assert storage.to_document(a.experiment)==before
            a.backend.set('python');a.start_button.invoke();a.pause_button.invoke()
            assert not a.running and a.future is None and a.experiment.settings.backend=='python'
            a.backend.set('rust');a.target.set('1');a.target_button.invoke()
            rec.until(root,lambda:entered.is_set());assert a.future is not None and not a.future.done()
            committed_before=storage.to_document(a.experiment)
            a.stop_button.invoke();assert a._stop_requested and not a.closed
            assert storage.to_document(a.experiment)==committed_before
            save_original=recovery.save_recovery;attempts=[]
            def fail_once(*args,**kw):
                attempts.append(True)
                if len(attempts)==1:raise OSError('406 controlled write failure before recovery publication')
                return save_original(*args,**kw)
            with patch.object(recovery,'save_recovery',fail_once):
                release.set();rec.until(root,lambda:a.future is None and not a._stop_requested)
                analytic(a.experiment,1.);assert not a.closed and len(messages)==1
                a.stop_button.invoke();assert not a.closed and len(attempts)==2
            stopped=storage.to_document(a.experiment);path=Path(a.last_recovery_path)
            assert storage.to_document(storage.load(path))==stopped
            q.atomic_json(d/'recovery-after1.json',json.loads(path.read_bytes()));checkpoints['stopped']=stopped
            with patch.object(module.filedialog,'asksaveasfilename',return_value=str(after_saved)):button(a,'Сохранить JSON').invoke()
            with patch.object(module.filedialog,'askopenfilename',return_value=str(path)):button(b,'Открыть JSON').invoke()
            assert storage.to_document(b.experiment)==stopped
            # A genuine user reload of the preserved dynamic state, not new Q2 integration.
            with patch.object(module.filedialog,'askopenfilename',return_value=str(source402)):button(b,'Открыть JSON').invoke()
            assert storage.to_document(b.experiment)==frame100
            view=b._show_inspection();rec.until(root,lambda:view.viewer is not None)
            assert all(inspection.TWO_Q2_EXPERIMENTAL_WARNING in f.get('1.0','end') for f in view.texts)
            assert view.payload['numerical_reliability']['qualification']['current_trajectory_certified'] is False
            view.close();view=None
            with patch.object(module.filedialog,'asksaveasfilename',return_value=str(two_saved)):button(b,'Сохранить JSON').invoke()
            assert storage.to_document(storage.load(two_saved))==frame100 and q.sha(source402)==two_sha
            root.update()
            for name,obj in [('zeroQ2',a),('twoQ2',b)]:
                layouts[name]=dict(width=obj.root.winfo_width(),height=obj.root.winfo_height(),canvas_height=obj.canvas.get_tk_widget().winfo_height())
            foreign=root.after(60000,lambda:None)
            b.close();assert not a.closed and foreign in root.tk.call('after','info')
            entered.clear();release.clear();a.target.set('2');a.target_button.invoke()
            rec.until(root,lambda:entered.is_set());assert a.future is not None and not a.future.done()
            wa.tk.call(wa.protocol('WM_DELETE_WINDOW'))
            assert not a.closed and a._close_requested and a.experiment.time==1.
            release.set();rec.until(root,lambda:a.closed)
            analytic(a.experiment,2.);final=storage.to_document(a.experiment)
            assert storage.to_document(storage.load(a.last_recovery_path))==final
            q.atomic_json(d/'recovery-after2.json',json.loads(Path(a.last_recovery_path).read_bytes()))
            checkpoints['closed']=final;count=len(native_calls);rec.pump(root)
            assert count==len(native_calls)>0 and len(calls)==2
            assert foreign in root.tk.call('after','info');root.after_cancel(foreign)
            assert q.sha(initial_saved)==initial_sha
            assert len(messages)==1 and '406 controlled write failure' in messages[0][1]
            assert not rec.errors and not rec.foreign_cancellations and not rec.queue(root)
            root.destroy();rec.pump(root);assert not rec.errors
        except BaseException:
            failure=traceback.format_exc();raise
        finally:
            release.set()
            # Persist before any exceptional cleanup; no invented state after failure.
            q.atomic_json(d/'result.json',dict(status='FAIL' if failure else 'PASS_REAL_PACKET_GUI_RECOVERY',failure=failure,
                candidate=P['candidate_commit'],plan_SHA256=q.sha(W/'gui-plan.json'),callbacks=rec.events,destroy=rec.destroys,
                background_errors=rec.errors,foreign_cancellations=rec.foreign_cancellations,
                messages=messages,real_completed_packets=calls,compiled_native_calls=len(native_calls),
                checkpoints=checkpoints,layouts=layouts,frame100_input_SHA256=two_sha,
                scope='Two genuine unchanged one-body packets with a pre-compute Event gate; not a mock numerical result or a new scientific qualification. Dynamic state load/save/inspection only; no Q2 orbit repeated.'))
            if view is not None:view.close()
            for obj in (b,a):
                if obj is not None and not obj.closed and obj.future is None:obj.close()
    assert hashlib.sha256((json.dumps(recipe.runtime_fingerprint('rust'),indent=2)+'\n').encode()).hexdigest()==P['source_fingerprint']
    print('PASS two real compiled-force packets, stop/writefailure/retry/reopen/activeWMclose; scheduledQ2inspector,dualwindowowners,0Tclerrors',flush=True)


if __name__=='__main__':main()
