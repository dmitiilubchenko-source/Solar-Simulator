"""Exact interface400 source-delta review; never an accuracy or release receipt."""
import ast
import hashlib
from pathlib import Path
import subprocess

BASE='f723a2162b4e115378959e244f428529be2d4516'
APPROVED={
    'src/solar_simulator/app.py':'d794a547bdf762604d9c1c593a01ec6ceaf558fa9f1c6454877c9942b144fde5',
    'src/solar_simulator/inspection.py':'2be1be8bac8a7b25348c838dbca0b02486aa95c311e33dc721bc68fef482116b',
    'src/solar_simulator/inspection_view.py':'c6b93b98c09edf3fabd20c21e5f8855ab45d88a2e652199cc387b9136925685d',
}


def sha(data):return hashlib.sha256(data).hexdigest()
def dump(node):return ast.dump(node,include_attributes=False)


def remove_exact(body,code):
    expected=ast.parse(code).body;n=len(expected)
    matches=[i for i in range(len(body)-n+1) if [dump(x) for x in body[i:i+n]]==[dump(x) for x in expected]]
    if len(matches)!=1:raise ValueError('Exact reviewed presentation sequence missing/duplicated')
    i=matches[0];return body[:i]+body[i+n:]


def strip_reviewed(name,tree):
    if name.endswith('/inspection.py'):
        tree.body=[n for n in tree.body if not (isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id=='TWO_Q2_EXPERIMENTAL_WARNING') and not (isinstance(n,ast.FunctionDef) and n.name=='experimental_q2_warning')]
        f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='report')
        f.body=remove_exact(f.body,'if len(experiment.rotations)==2:\n    limitations.append(experimental_q2_warning(experiment.rotations))')
    elif name.endswith('/inspection_view.py'):
        f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='rotation_text')
        f.body=remove_exact(f.body,"from .inspection import experimental_q2_warning\nwarning=experimental_q2_warning(payload['rotations'])\nif warning:lines[:0]=[warning,'']")
    elif name.endswith('/app.py'):
        cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Laboratory')
        f=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='_update_profile_info')
        conditional=next(n for n in f.body if isinstance(n,ast.If))
        conditional.body=remove_exact(conditional.body,"from .inspection import experimental_q2_warning\nwarning=experimental_q2_warning(self.experiment.rotations)\nif warning:self.model_info.set(self.model_info.get()+' '+warning)")
    else:raise ValueError('Unreviewed presentation path')
    return tree


def review_maps(base,target):
    """Pure bytes/AST negative-test seam, no IO/model execution or file mutation."""
    if set(base)!=set(target):raise ValueError('Source inventory changed')
    changed={n for n in base if base[n]!=target[n]}
    if changed!=set(APPROVED):raise ValueError('Unexpected numerical/source delta: '+repr(sorted(changed)))
    rows=[]
    for name in sorted(base):
        if name not in changed:
            if name.endswith('.py') and dump(ast.parse(base[name]))!=dump(ast.parse(target[name])):raise ValueError('Protected AST changed')
            continue
        if sha(target[name])!=APPROVED[name]:raise ValueError('Not the exact reviewed presentation patch: '+name)
        if dump(ast.parse(base[name]))!=dump(strip_reviewed(name,ast.parse(target[name]))):raise ValueError('Changes outside reviewed presentation nodes: '+name)
        rows.append(dict(path=name,base_SHA256=sha(base[name]),target_SHA256=sha(target[name]),remaining_module_AST_exact=True))
    return dict(status='PRESENTATION_ONLY_DELTA_CONFIRMED_NOT_ACCURACY_QUALIFICATION',base_commit=BASE,changed=rows,
        protected_files=len(base)-len(changed),protected_SHA256={n:sha(base[n]) for n in sorted(base) if n not in changed},
        release_approved=False,application_acceptance_performed=False,
        scope='Exact patch only, f723a216 + fixed58 evidence399. Not the fe0f456/391 whitelist or historical receipt migration.')


def git(root,*args):return subprocess.check_output(['git','-C',str(root),*args])


def blobs(root,revision,names):
    import io
    data=subprocess.check_output(['git','-C',str(root),'cat-file','--batch'],input=''.join(revision+':'+n+'\n' for n in names).encode())
    stream=io.BytesIO(data);result={}
    for name in names:
        header=stream.readline().decode().split();result[name]=stream.read(int(header[2]))
        if stream.read(1)!=b'\n':raise ValueError('Corrupt Git blob stream')
    return result


def source_maps(base_root,target_root):
    base_root=Path(base_root);target_root=Path(target_root)
    if git(base_root,'rev-parse','HEAD').decode().strip()!=BASE or git(base_root,'status','--porcelain').strip():raise ValueError('Wrong/dirty optimized baseline')
    names=git(base_root,'ls-tree','-r','--name-only',BASE,'--','src','rust','pyproject.toml','.gitattributes').decode().splitlines()
    changes=set(git(target_root,'diff','--name-only',BASE,'--').decode().splitlines())
    if changes!=set(APPROVED):raise ValueError('Candidate delta outside exact three presentation files')
    if git(target_root,'ls-files','--others','--exclude-standard','--','src','rust').strip():raise ValueError('Untracked runtime/native source')
    other=[n for n in names if not n.startswith('src/')]
    base=blobs(base_root,BASE,other);target=blobs(target_root,'HEAD',other)
    for name in names:
        if name.startswith('src/'):
            base[name]=(base_root/name).read_bytes();target[name]=(target_root/name).read_bytes()
    return base,target


def review(base_root,target_root):
    a,b=source_maps(base_root,target_root);result=review_maps(a,b)
    result['representations']='Materialized src bytes including IC/data; exact Git blobs for Rust/metadata; working delta restricted to exact3 approved paths.'
    return result
