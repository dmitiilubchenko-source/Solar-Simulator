"""Fail-closed text-only whitelist for the existing two-Q2 warning."""
import ast,hashlib
NAME='TWO_Q2_EXPERIMENTAL_WARNING'
def compare(old,new):
 def locate(raw):
  tree=ast.parse(raw);nodes=[x for x in tree.body if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id==NAME for t in x.targets)]
  if len(nodes)!=1 or len(nodes[0].targets)!=1 or not isinstance(nodes[0].value,ast.Constant) or type(nodes[0].value.value) is not str:raise ValueError('Expected one existing literal warning')
  return tree,nodes[0]
 a,x=locate(old);b,y=locate(new);la=old.splitlines(keepends=True);lb=new.splitlines(keepends=True)
 if b''.join(la[:x.lineno-1])!=b''.join(lb[:y.lineno-1]) or b''.join(la[x.end_lineno:])!=b''.join(lb[y.end_lineno:]):raise ValueError('Bytes changed outside warning assignment')
 before=x.value.value;after=y.value.value;x.value=ast.Constant(value='allowed403literal');y.value=ast.Constant(value='allowed403literal')
 if ast.dump(a,include_attributes=False)!=ast.dump(b,include_attributes=False):raise ValueError('Nonliteral/structural change outside allowed text')
 return dict(status='PASS_ONE_LITERAL_ONLY',old_SHA256=hashlib.sha256(old).hexdigest(),new_SHA256=hashlib.sha256(new).hexdigest(),old_text=before,new_text=after,all_other_AST_and_bytes_exact=True)
