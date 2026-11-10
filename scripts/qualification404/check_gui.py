"""Source-bound nonorbital teardown/worker/recovery acceptance404."""
import json,sys,time,traceback,subprocess,hashlib
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from scripts import q2_execution398 as q
W=R/'.tools/qualification404-20261108';PLAN=R/'scripts/qualification404/plan.json'
class Recorder:
 def __init__(self):self.name='setup';self.events=[];self.errors=[];self.destroys=[];self.apps=[];self.roots=[];self.entries={};self.interpreters={};self.foreign_cancellations=[]
 def attach(self,root):
  key=id(root.tk)
  if key in self.interpreters:return
  self.interpreters[key]=root;self.roots.append(root)
  def error(message,info):self.errors.append(dict(case=self.name,kind='Tcl',message=message,errorInfo=info,elapsed=time.perf_counter()))
  root.tk.createcommand('capture404_background',error);root.tk.eval('proc bgerror {message} {capture404_background $message $::errorInfo}')
  root._root().report_callback_exception=lambda typ,value,tb:self.errors.append(dict(case=self.name,kind='Python',message=str(value),traceback=''.join(traceback.format_exception(typ,value,tb))))
 def queue(self,root):
  rows=[]
  for ident in root.tk.call('after','info'):
   script,kind=root.tk.call('after','info',ident);command=root.tk.splitlist(script)[0];entry=self.entries.get((id(root.tk),ident))
   rows.append(dict(after_id=ident,command=command,kind=kind,owner=None if entry is None else entry['owner'],command_exists=bool(root.tk.call('info','commands',command))))
  return rows
 def own(self,root,rows):
  prefix=str(root)
  return [r for r in rows if r['owner'] is not None and (prefix=='.' or r['owner']==prefix or r['owner'].startswith(prefix+'.'))]
 def pump(self,root,seconds=.075):
  end=time.perf_counter()+seconds
  while True:
   root.tk.call('update')
   if time.perf_counter()>=end:break
   time.sleep(.005)
 def until(self,root,predicate):
  end=time.perf_counter()+3
  while not predicate():
   root.tk.call('update');time.sleep(.005)
   if time.perf_counter()>end:raise TimeoutError('Controlled GUI worker did not finish')
 def instrument(self,tk,Lab):
  rec=self;after=tk.Misc.after;cancel=tk.Misc.after_cancel;init=Lab.__init__;destroy=Lab._destroy
  def traced_after(widget,ms,func=None,*args,**kwargs):
   ident=after(widget,ms,func,*args,**kwargs)
   if func is not None:
    script=widget.tk.call('after','info',ident)[0]
    row=dict(case=rec.name,event='schedule',after_id=ident,command=str(script),owner=str(widget),interpreter=id(widget.tk),delay=str(ms),callback=getattr(func,'__qualname__',repr(func)),elapsed=time.perf_counter())
    rec.events.append(row);rec.entries[(id(widget.tk),ident)]=row
   return ident
  def traced_cancel(widget,ident):
   entry=rec.entries.get((id(widget.tk),ident))
   if entry is not None and entry['owner']!=str(widget):rec.foreign_cancellations.append(dict(after_id=ident,registered_owner=entry['owner'],cancelling_owner=str(widget)))
   result=cancel(widget,ident);rec.events.append(dict(case=rec.name,event='cancel',after_id=ident,owner=str(widget),interpreter=id(widget.tk),elapsed=time.perf_counter()));return result
  def traced_init(app,root,*a,**kw):init(app,root,*a,**kw);rec.attach(root);rec.apps.append(app)
  def traced_destroy(app):
   before=rec.own(app.root,rec.queue(app.root));closed=app.closed
   try:result=destroy(app)
   except BaseException as error:
    rec.destroys.append(dict(case=rec.name,status='REJECTED_BEFORE_DESTROY',error=str(error),before=before,closed=app.closed));raise
   remaining=rec.own(app.root,rec.queue(app.root));rec.destroys.append(dict(case=rec.name,status='CLOSED' if app.closed else 'OPEN',already_closed=closed,before=before,after=remaining,elapsed=time.perf_counter()))
   if app.closed:assert not remaining,'Owned callbacks survived destroy'
   return result
  stack=ExitStack();stack.enter_context(patch.object(tk.Misc,'after',traced_after));stack.enter_context(patch.object(tk.Misc,'after_cancel',traced_cancel));stack.enter_context(patch.object(Lab,'__init__',traced_init));stack.enter_context(patch.object(Lab,'_destroy',traced_destroy));return stack
def main():
 p=json.loads(PLAN.read_bytes());binding=json.loads((W/'candidate.json').read_bytes());root=Path(p['new_source']);sys.path.insert(0,str(root/'src'))
 import tkinter as tk,solar_simulator,solar_native,numpy,scipy,matplotlib
 from solar_simulator import app as module,storage,experiment,accuracy,nbody_rotation,recovery,application_profiles
 from solar_simulator.control_row import ControlRow
 from scripts.q2_source_adapter396 import require_origins
 require_origins(solar_simulator.__file__,[numpy.__file__,scipy.__file__,solar_native.__file__],root,sys.prefix,Path(p['interpreter']).parents[1])
 assert subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()==binding['commit'] and not subprocess.check_output(['git','-C',str(root),'status','--porcelain'])
 q.require_sha(getattr(solar_native,'solar_native',solar_native).__file__,p['native_SHA256'])
 saved=R/'.tools/qualification402-20261108/jobs/main__python__gui__cold/frame-100.json';document=json.loads(saved.read_bytes());state=storage.from_document(document);rec=Recorder();evolution=[];ui=[];outcomes=[]
 def forbidden(*a,**kw):evolution.append(True);raise AssertionError('No physical evolution permitted404')
 def lab():
  root=tk.Tk();root.withdraw();return module.Laboratory(root,state)
 def unchanged(app,expected=document):assert storage.to_document(app.experiment)==expected
 def close(app):
  app.close();assert app.closed and app.future is None and app._poll_after_id is None
  rec.pump(app.root);unchanged(app)
  app.close();app._destroy();app._request_close();app._poll();rec.pump(app.root,.015)
  assert app.closed and app.pool._shutdown
 def save_check(app,label):
  path=Path(app.last_recovery_path);assert storage.to_document(storage.load(path))==document
  expected=R/'.tools/qualification403-20261108/lifecycle/active_close_recovery/recovery-original.json';assert path.read_bytes()==expected.read_bytes()
  target=W/'cases'/rec.name/(label+'.json');target.write_bytes(path.read_bytes());return dict(path=str(path),sha256=q.sha(path),expected403_SHA256=q.sha(expected))
 def worker_case(mode):
  from threading import Event
  app=lab();started=Event();release=Event();finished=Event();count=[]
  def inert(current,steps):
   assert steps==1 and storage.to_document(current)==document;started.set();assert release.wait(2);count.append('finished');finished.set()
   if mode=='worker_failure':raise RuntimeError('controlled worker failure404')
   return current
  with patch.object(module,'advance',inert):
   app.step_button.invoke();assert started.wait(1) and app.future is not None
   try:
    if mode=='active_programmatic_close':app.close()
    elif mode in ('active_request_close','active_worker_save_failure_retry'):app._request_close()
    elif mode=='stop_keeps_window':app._stop_and_save()
    if mode.startswith('active_') or mode=='stop_keeps_window':assert not app.closed and not app.running and not app.future.done()
    if mode=='active_worker_save_failure_retry':
     with patch.object(recovery,'save_recovery',side_effect=OSError('controlled full disk404')):
      release.set();rec.until(app.root,lambda:app.future is None)
     assert not app.closed and app.last_recovery_path is None and app._poll_after_id in app.root.tk.call('after','info');unchanged(app)
     app._request_close();assert app.closed
    else:
     release.set();rec.until(app.root,lambda:app.future is None)
     if mode in ('active_programmatic_close','active_request_close'):assert app.closed
     else:
      assert not app.closed;unchanged(app)
      if mode in ('stop_keeps_window','worker_failure'):save_check(app,'before-close-recovery')
      app._request_close();assert app.closed
    assert finished.is_set() and len(count)==1;save_check(app,'final-recovery');unchanged(app)
    rec.pump(app.root);assert len(count)==1
    try:app.pool.submit(lambda:None)
    except RuntimeError:pass
    else:raise AssertionError('Closed executor accepted a new task')
   finally:release.set()
  return dict(worker_finished_before_close=True,submitted_packets=1,no_postclose_calculation=True)
 def run(identifier):
  if identifier.endswith('_figures_close') or identifier in ('one_figure_close','two_figures_pending_all'):
   if identifier=='zero_figures_close':s=application_profiles.scenario('sun-earth')
   elif identifier=='one_figure_close':s=application_profiles.lunar_rotation()
   else:s=state
   root=tk.Tk();root.withdraw();app=module.Laboratory(root,s);before=storage.to_document(s);app.close();rec.pump(root);assert storage.to_document(app.experiment)==before
   app.close();app._destroy();return dict(figures=len(s.rotations),repeated_close_safe=True)
  if identifier=='manual_and_scheduled_poll':
   app=lab()
   for _ in range(5):
    app._poll();owned=rec.own(app.root,rec.queue(app.root));assert sum(x['command'].endswith('_poll') for x in owned)==1
   rec.pump(app.root,.13);assert app._poll_after_id in app.root.tk.call('after','info')
   owned=rec.own(app.root,rec.queue(app.root));assert sum(x['command'].endswith('_poll') for x in owned)==1
   close(app);return dict(manual_calls=5,parallel_poll_loops=1,normal_delay_ms=40)
  if identifier in ('controlrow_owners_and_repeat_destroy','executing_layout_destroy'):
   root=tk.Tk();root.withdraw();rec.attach(root)
   if identifier=='executing_layout_destroy':
    class DuringLayout(ControlRow):
     def _layout(self):self.destroy();super()._layout()
    first=DuringLayout(root)
   else:first=ControlRow(root)
   second=ControlRow(root);first.add(tk.ttk.Label(first,text='first'));second.add(tk.ttk.Label(second,text='second'));other=second.pending
   if identifier=='executing_layout_destroy':rec.pump(root,.02)
   else:first.destroy();assert other in root.tk.call('after','info');rec.pump(root,.02)
   first.destroy();first._schedule();assert first.pending is None and first._closing
   assert second.winfo_exists() and second.pending is None
   second.destroy();second.destroy();root.destroy();rec.pump(root);return dict(own_row_only=True,already_running_layout_safe=True)
  if identifier=='canvas_event_loop_cleanup':
   app=lab();app.root.after(0,app.close);app.canvas.start_event_loop(.3);assert app.closed and app.canvas._event_loop_id is None and app.canvas._idle_draw_id is None;rec.pump(app.root);return dict(real_backend_event_loop=True)
  if identifier in ('completed_worker','active_programmatic_close','active_request_close','stop_keeps_window','worker_failure','active_worker_save_failure_retry'):return worker_case(identifier)
  if identifier=='save_failure_retry':
   app=lab()
   with patch.object(recovery,'save_recovery',side_effect=OSError('controlled save failure404')):app._request_close()
   assert not app.closed and app.root.winfo_exists() and app.last_recovery_path is None;unchanged(app)
   assert app._poll_after_id in app.root.tk.call('after','info');app._request_close();assert app.closed;save_check(app,'retry-recovery');rec.pump(app.root);return dict(failure_kept_window=True,retry_success=True)
  if identifier in ('two_windows_and_foreign_callbacks','canvas_contract_and_foreign_owner'):
   host=tk.Tk();host.withdraw();rec.attach(host);one=module.Laboratory(tk.Toplevel(host),state);two=module.Laboratory(tk.Toplevel(host),state)
   foreign=two.canvas._idle_draw_id;original=one.canvas._idle_draw_id;widget=one.canvas.get_tk_widget();sentinel=[];timer=host.after(80,lambda:sentinel.append(True))
   if identifier=='canvas_contract_and_foreign_owner':
    one.canvas._idle_draw_id=foreign
    try:one.close()
    except RuntimeError:pass
    else:raise AssertionError('Foreign canvas timer cancelled')
    assert not one.closed and foreign in host.tk.call('after','info');one.canvas._idle_draw_id=original
    value=one.canvas._event_loop_id;del one.canvas._event_loop_id
    try:one.close()
    except RuntimeError:pass
    else:raise AssertionError('Unknown canvas contract accepted')
    assert not one.closed;one.canvas._event_loop_id=value
   one.close();assert foreign in host.tk.call('after','info') and two._poll_after_id in host.tk.call('after','info') and timer in host.tk.call('after','info')
   rec.pump(host,.1);assert sentinel==[True] and not two.closed;unchanged(two)
   two.close();rec.pump(host);host.destroy();rec.pump(host);return dict(foreign_canvas_and_timer_preserved=True,contract_failure_before_destroy=True)
  if identifier=='resize_layout_draw':
   app=lab();app.root.deiconify();app.root.geometry('1180x820');rec.pump(app.root,.04)
   rows=[x for x in app.root.winfo_children() if isinstance(x,ControlRow)];assert rows
   before=[x.winfo_width() for x in rows];app.root.geometry('880x820');app.canvas.draw_idle();rec.pump(app.root,.06)
   after=[x.winfo_width() for x in rows];assert max(before)>max(after) and all(x.winfo_height()>0 for x in rows)
   assert all(item.place_info() for row in rows for item in row.items);unchanged(app);close(app);return dict(wide=before,narrow=after,layout_enabled=True,draw_enabled=True)
  if identifier=='user_save_load':
   app=lab();path=W/'cases'/identifier/'user.json'
   with patch.object(module.filedialog,'asksaveasfilename',return_value=str(path)):app._save()
   raw=path.read_bytes()
   with patch.object(module.filedialog,'askopenfilename',return_value=str(path)):app._load()
   unchanged(app);assert path.read_bytes()==raw
   with patch.object(module.filedialog,'asksaveasfilename',return_value=''):app._save()
   with patch.object(module.filedialog,'askopenfilename',return_value=''):app._load()
   unchanged(app);close(app);return dict(save_load_and_cancel_exact=True)
  raise ValueError('Unplanned case')
 with rec.instrument(tk,module.Laboratory),patch.object(experiment,'advance',forbidden),patch.object(accuracy,'evolve_accurate',forbidden),patch.object(nbody_rotation,'integrate',forbidden),patch.object(nbody_rotation,'solve_ivp',forbidden),patch.object(solar_native,'point_acceleration',forbidden),patch.object(module.messagebox,'showerror',side_effect=lambda *a,**k:ui.append(dict(case=rec.name,args=list(a)))):
  for identifier in p['post_cases']:
   rec.name=identifier;directory=W/'cases'/identifier;directory.mkdir(parents=True,exist_ok=False);starts=(len(rec.events),len(rec.errors),len(rec.destroys),len(ui));cpu=time.process_time();wall=time.perf_counter();failure=None;result=None
   try:
    result=run(identifier);assert not rec.errors[starts[1]:] and not rec.foreign_cancellations and not evolution
    expected={'worker_failure':'controlled worker failure404','save_failure_retry':'controlled save failure404','active_worker_save_failure_retry':'controlled full disk404'}
    messages=ui[starts[3]:]
    if identifier in expected:assert len(messages)==1 and expected[identifier] in str(messages[0]['args'])
    else:assert not messages,'Unexpected GUI error notification'
   except BaseException as error:failure=dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc())
   payload=dict(id=identifier,status='FAIL' if failure else 'PASS',source=binding,plan_SHA256=q.sha(PLAN),tools_SHA256=q.sha(W/'tools-v2.json'),result=result,failure=failure,callbacks=rec.events[starts[0]:],errors=rec.errors[starts[1]:],destroy=rec.destroys[starts[2]:],UI_messages=ui[starts[3]:],evolution_calls=len(evolution),foreign_cancellations=rec.foreign_cancellations,CPU_seconds=time.process_time()-cpu,wall_seconds=time.perf_counter()-wall)
   q.atomic_json(directory/'result.json',payload)
   if failure:raise RuntimeError('404acceptance failed:'+identifier+' '+failure['message'])
   q.atomic_json(directory/'complete.json',q.envelope(dict(source=binding,case=identifier,result_SHA256=q.sha(directory/'result.json'),files={x.name:dict(size=x.stat().st_size,sha256=q.sha(x)) for x in directory.iterdir() if x.is_file()})))
   outcomes.append(identifier);print('PASS',identifier,flush=True)
 assert not rec.errors and not evolution and len(outcomes)==len(p['post_cases'])
 q.atomic_json(W/'acceptance.json',dict(status='PASS_CONTROLLED_LIFECYCLE_AND_RECOVERY',cases=outcomes,bgerrors=rec.errors,evolution_calls=0,source=binding,actual_import=solar_simulator.__file__,dependency_prefix=sys.prefix,Matplotlib=matplotlib.__version__,no_orbits=True,limitations='Actual executor returns saved402frame100; no numerical solver tests. Embedded cleanup uses validated private TkAgg ownership contract on qualified version.'))
if __name__=='__main__':main()
