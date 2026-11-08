"""Nonorbital Tcl ownership probes on exacta99. Production files stay untouched."""
import json,sys,time,traceback,re
from pathlib import Path
from unittest.mock import patch
R=Path(__file__).resolve().parents[2];sys.path.insert(0,str(R))
from scripts import q2_execution398 as q
W=R/'.tools/qualification403-20261108';PLAN=R/'scripts/qualification403/plan.json'
def main():
 p=json.loads(PLAN.read_bytes());case=globals().get('CASE_OVERRIDE') or next(x for x in p['lifecycle_cases'] if x['id']==sys.argv[1]);root_source=Path(p['original_source']);sys.path.insert(0,str(root_source/'src'))
 import solar_simulator,tkinter as tk,solar_native
 from solar_simulator import app as module,experiment,accuracy,nbody_rotation,storage
 assert Path(solar_simulator.__file__).resolve().is_relative_to(root_source/'src')
 import subprocess
 assert subprocess.check_output(['git','-C',str(root_source),'rev-parse','HEAD'],text=True).strip()==p['original_commit']
 q.require_sha(getattr(solar_native,'solar_native',solar_native).__file__,p['native_SHA256'])
 directory=W/'lifecycle'/case['id'];directory.mkdir(parents=True,exist_ok=False)
 starts=time.perf_counter();events=[];errors=[];roots=[];snapshots=[];calls=dict(evolution=0,synthetic_workers=0);active_root=[None]
 saved=json.loads((R/'.tools/qualification402-20261108/jobs/main__python__gui__cold/frame-100.json').read_bytes());initial=storage.from_document(saved)
 def forbidden(*a,**kw):calls['evolution']+=1;raise AssertionError('No evolution allowed403')
 original_after=tk.Misc.after
 def traced_after(self,ms,func=None,*args):
  ident=original_after(self,ms,func,*args)
  if func is not None:
   try:script=self.tk.call('after','info',ident)[0]
   except tk.TclError:script=None
   events.append(dict(event='scheduled',elapsed=time.perf_counter()-starts,after_id=ident,script=str(script),widget=str(self),callback=getattr(func,'__qualname__',repr(func)),root=active_root[0],stack=[dict(file=x.filename,line=x.lineno,function=x.name) for x in traceback.extract_stack(limit=12)[:-1]]))
  return ident
 def queue(root):
  rows=[]
  for ident in root.tk.call('after','info'):
   try:
    script,kind=root.tk.call('after','info',ident);command=root.tk.splitlist(script)[0]
    rows.append(dict(id=ident,script=str(script),kind=str(kind),command=str(command),command_exists=bool(root.tk.call('info','commands',command))))
   except tk.TclError:pass
  return rows
 def install_bg(root,index):
  def capture(message,info):errors.append(dict(message=message,errorInfo=info,root=index,elapsed=time.perf_counter()-starts))
  root.tk.createcommand('diag403_background',capture)
  root.tk.eval('proc bgerror {message} {diag403_background $message $::errorInfo}')
 def pump(root):
  root.tk.call('update');time.sleep(.06);root.tk.call('update')
 def cancel_unwanted(root,keep):
  cancelled=[]
  for row in queue(root):
   group='poll' if row['command'].endswith('_poll') else 'layout' if row['command'].endswith('_layout') else 'idle' if row['command'].endswith('idle_draw') else 'other'
   if group!=keep:
    event=next((x for x in reversed(events) if x['after_id']==row['id'] and x['root']==active_root[0]),None)
    if event is None:root.tk.call('after','cancel',row['id'])
    else:root.nametowidget(event['widget']).after_cancel(row['id'])
    cancelled.append(row)
  return cancelled
 with patch.object(tk.Misc,'after',traced_after),patch.object(experiment,'advance',forbidden),patch.object(accuracy,'evolve_accurate',forbidden),patch.object(nbody_rotation,'integrate',forbidden),patch.object(nbody_rotation,'solve_ivp',forbidden),patch.object(solar_native,'point_acceleration',forbidden):
  for index in range(case['roots']):
   active_root[0]=index;root=tk.Tk();root.withdraw();roots.append(root);install_bg(root,index);app=module.Laboratory(root,initial)
   before=storage.to_document(app.experiment);assert before==saved
   pending_before=[];watchdog=[None];destroy=app._destroy
   def observed_destroy():
    pending_before.extend(queue(root))
    if watchdog[0] is not None:root.after_cancel(watchdog[0]);watchdog[0]=None
    return destroy()
   app._destroy=observed_destroy
   mode=case['mode'];cancelled=[]
   if mode.startswith('isolate-') or mode=='cancel-all':cancelled=cancel_unwanted(root,mode.split('-',1)[1] if mode.startswith('isolate-') else 'none')
   errors_before=len(errors);worker=[]
   if mode in ('completed-worker','active-close'):
    from threading import Event
    gate=Event()
    def synthetic(state,steps):
     calls['synthetic_workers']+=1;assert steps==1 and storage.to_document(state)==saved
     if mode=='active-close':assert gate.wait(2)
     return state
    def watch():
     if app.future is None and worker:
      assert storage.to_document(app.experiment)==saved;app.close()
     elif not app.closed:root.after(5,watch)
    with patch.object(module,'advance',synthetic),patch.object(module.messagebox,'showerror',side_effect=lambda *a,**k:errors.append(dict(message=str(a),root=index,kind='unexpected_UIerror'))):
     app.step_button.invoke();assert app.future is not None;worker.append(True)
     if mode=='active-close':
      app.close();root.after(10,gate.set)
     else:root.after(5,watch)
     watchdog[0]=root.after(2500,lambda:root.quit());root.mainloop()
     assert app.closed and app.future is None
   else:
    if mode=='multi-pumped':pump(root)
    pending=queue(root);app.close()
   pending_after=queue(root)
   if mode in ('single-pump','completed-worker','active-close','cancel-all') or mode.startswith('isolate-'):pump(root)
   assert storage.to_document(app.experiment)==before
   recovery=None
   if mode=='active-close':
    path=Path(app.last_recovery_path);assert storage.to_document(storage.load(path))==before
    (directory/'recovery-original.json').write_bytes(path.read_bytes())
    recovery=dict(path=str(path),sha256=q.sha(path),saved_q_S_settings_exact=True)
   snapshot=dict(root=index,mode=mode,closed=True,worker_done=app.future is None,state_unchanged=True,after_destroy=pending_after,cancelled=cancelled,recovery=recovery,errors_since_start=len(errors)-errors_before)
   if mode in ('single-pump','completed-worker','active-close','cancel-all') or mode.startswith('isolate-'):snapshot['after_pump']=queue(root)
   snapshot['before_destroy']=pending_before
   snapshots.append(snapshot)
  if case['mode']=='multi-pumped':pump(roots[-1])
 q.atomic_json(directory/'result.json',dict(case=case,source_commit=p['original_commit'],source_root=str(root_source),plan_SHA256=q.sha(PLAN),events=events,errors=errors,snapshots=snapshots,counters=calls,original402_raw_log_has_timestamps=False,unmodified_source=True,orbit_integrations=0))
 print(json.dumps(dict(case=case['id'],errors=len(errors),evolution_calls=calls['evolution'],callbacks=sorted({re.sub(r'^\d+','',e['message'].split('"')[1]) for e in errors if 'invalid command name' in e.get('message','')}))),flush=True)
if __name__=='__main__':
 if sys.argv[1]=='remaining-batch':
  continuation=json.loads((W/'continuation-v2.json').read_bytes())
  for old in continuation['reused_six_complete']:
   q.require_sha(W/'lifecycle'/old['id']/'complete.json',old['receipt_SHA256']);q.require_sha(W/'lifecycle'/old['id']/'result.json',old['result_SHA256'])
  for case in continuation['new_cases']:
   CASE_OVERRIDE=case;main();path=W/'lifecycle'/case['id']/'result.json'
   q.atomic_json(path.parent/'complete.json',q.envelope(dict(case=case,plan_SHA256=q.sha(PLAN),continuation_SHA256=q.sha(W/'continuation-v2.json'),tools_SHA256=q.sha(W/'tools-v2.json'),result_SHA256=q.sha(path),worker_SHA256=q.sha(Path(__file__)))))
 else:main()
