"""Separate lifecycle scope guard404; never a presentation-only whitelist."""
import ast,copy,hashlib
def dump(x):return ast.dump(x,include_attributes=False)
def node(text):return ast.parse(text).body[0]
def protected_rest(old,new,klass,allowed):
 """Other methods/imports/bytes must be exact; blank separators belong to methods."""
 def mask(raw):
  tree=ast.parse(raw);cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name==klass);lines=raw.splitlines(keepends=True);spans=[]
  for x in cls.body:
   if isinstance(x,ast.FunctionDef) and x.name in allowed:
    end=x.end_lineno
    while end<len(lines) and not lines[end].strip():end+=1
    spans.append((x.lineno-1,end))
  for start,end in reversed(spans):lines[start:end]=[]
  cls.body=[x for x in cls.body if not isinstance(x,ast.FunctionDef) or x.name not in allowed]
  return dump(tree),b''.join(lines)
 a,b=mask(old),mask(new)
 if a!=b:raise ValueError('Unapproved method/import/byte change outside lifecycle scope')
def compare(app_old,app_new,row_old,row_new):
 allowed_app={'__init__','_poll','_destroy','_cancel_poll','_cancel_canvas_callbacks'};allowed_row={'__init__','_schedule','_layout','destroy'}
 protected_rest(app_old,app_new,'Laboratory',allowed_app);protected_rest(row_old,row_new,'ControlRow',allowed_row)
 def methods(raw,name):return {x.name:x for c in ast.parse(raw).body if isinstance(c,ast.ClassDef) and c.name==name for x in c.body if isinstance(x,ast.FunctionDef)}
 a,b=methods(app_old,'Laboratory'),methods(app_new,'Laboratory');r,s=methods(row_old,'ControlRow'),methods(row_new,'ControlRow')
 def eq(x,y):
  if dump(x)!=dump(y):raise ValueError('Lifecycle change altered protected dispatch/layout body')
 def is_poll_assign(x):return isinstance(x,ast.Assign) and len(x.targets)==1 and dump(x.targets[0])==dump(ast.parse('self._poll_after_id = 0').body[0].targets[0]) and isinstance(x.value,ast.Call)
 def normalize_poll_assignment(f):
  count=0
  class Normalize(ast.NodeTransformer):
   def visit_Assign(self,x):
    nonlocal count
    if is_poll_assign(x):
     eq(x.value,ast.parse('self.root.after(40,self._poll)').body[0].value);count+=1;return ast.Expr(value=x.value)
    return x
  out=Normalize().visit(copy.deepcopy(f));assert count==1;return out
 init=copy.deepcopy(b['__init__']);target=node('self._poll_after_id = None');matches=[x for x in init.body if dump(x)==dump(target)];assert len(matches)==1;init.body=[x for x in init.body if dump(x)!=dump(target)];eq(a['__init__'],normalize_poll_assignment(init))
 poll=copy.deepcopy(b['_poll']);eq(poll.body.pop(0),node('self._cancel_poll()'));eq(a['_poll'],normalize_poll_assignment(poll))
 destroy=copy.deepcopy(b['_destroy']);eq(destroy.body.pop(0),node('if self.closed:return'));eq(destroy.body[1],node('self._cancel_canvas_callbacks()'));eq(destroy.body[2],node('self._cancel_poll()'));destroy.body[1:3]=[];eq(a['_destroy'],destroy)
 rowinit=copy.deepcopy(s['__init__']);target=node('self._closing = False');assert sum(dump(x)==dump(target) for x in rowinit.body)==1;rowinit.body=[x for x in rowinit.body if dump(x)!=dump(target)];eq(r['__init__'],rowinit)
 schedule=copy.deepcopy(s['_schedule']);eq(schedule.body.pop(0),node('if self._closing:return'));eq(r['_schedule'],schedule)
 layout=copy.deepcopy(s['_layout']);eq(layout.body.pop(0),node('if self._closing:return'));cancel=layout.body.pop(0);eq(cancel,node("if self.pending is not None and self.pending in self.tk.call('after','info'):self.after_cancel(self.pending)"));eq(r['_layout'],layout)
 calls={
  '_cancel_poll':{'self.root.tk.call','self.root.after_cancel'},
  '_cancel_canvas_callbacks':{'self.canvas.get_tk_widget','set','widget.tk.call','hasattr','RuntimeError','getattr','type','widget.tk.splitlist','command.endswith','callbacks.append','widget.after_cancel','setattr'},
  'destroy':{'self.tk.call','self.after_cancel','super','super().destroy'}}
 for name,f in [('_cancel_poll',b['_cancel_poll']),('_cancel_canvas_callbacks',b['_cancel_canvas_callbacks']),('destroy',s['destroy'])]:
  actual={ast.unparse(x.func) for x in ast.walk(f) if isinstance(x,ast.Call)}
  if actual-calls[name] or any(isinstance(x,(ast.Try,ast.Import,ast.ImportFrom)) for x in ast.walk(f)):raise ValueError('Unexpected lifecycle helper call or error suppression')
  if any(isinstance(x,ast.Attribute) and x.attr in ('experiment','settings','bodies','rotations','future') for x in ast.walk(f)):raise ValueError('Lifecycle helper accesses numerical state/worker')
 return dict(status='PASS_REVIEWED_GUI_LIFECYCLE_SCOPE_NOT_PRESENTATION_ONLY',poll_interval_ms=40,dispatch_and_recovery_AST_exact=True,geometry_layout_AST_exact=True,all_other_AST_bytes_exact=True,new_helpers_call_allowlists=True,source_SHA256={k:hashlib.sha256(v).hexdigest() for k,v in [('app_old',app_old),('app_new',app_new),('row_old',row_old),('row_new',row_new)]})
