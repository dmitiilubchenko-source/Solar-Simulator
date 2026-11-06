"""Source-bound diagnostic frame substitution, not a production integrator.

Only center/drift assignments differ; solver, RHS, constants and tolerances
remain the existing implementation. Both variants create a NEW cold solver.
"""
import ast
import copy
import hashlib
import inspect
import math
from pathlib import Path
from types import ModuleType
import numpy as np

SOURCE_SHA256='7cdbf09b398aa467ec5badabcf4428c88dfc62ac81f49b73c988ae8c81c9ce7c'


def _frame_vector(value):
    """Explicit JSON/builtin-only SI triplet; inspect before float coercion."""
    if type(value) not in (tuple,list) or len(value)!=3:
        raise ValueError('Frame requires a three-component builtin vector')
    result=[]
    for x in value:
        if type(x) not in (int,float):raise ValueError('Frame requires real builtin scalars, excluding bool')
        try:v=float(x)
        except OverflowError as error:raise ValueError('Frame is not finite') from error
        if not math.isfinite(v):raise ValueError('Frame is not finite')
        result.append(v)
    array=np.array(result,dtype=float);array.setflags(write=False)
    return array


def clone_integrate(module,*,center=None,drift=None):
    """Clone trusted frozen function, replacing precisely two AST values.

    center is fixed-frame origin at this packet's start [m], drift its fixed
    inertial velocity [m/s]. Local solve times stay [0,duration]. None/None
    produces an unchanged-source control. No state/controller continuation.
    """
    if (center is None)!=(drift is None):raise ValueError('Both frame vectors are required')
    vectors=None if center is None else (_frame_vector(center),_frame_vector(drift))
    if not isinstance(module,ModuleType) or not getattr(module,'__file__',None):raise ValueError('Invalid source module')
    path=Path(module.__file__)
    if hashlib.sha256(path.read_bytes()).hexdigest()!=SOURCE_SHA256:raise ValueError('Frozen Q2 source SHA mismatch')
    function=getattr(module,'integrate',None)
    if (not inspect.isfunction(function) or function.__name__!='integrate'
            or function.__globals__ is not module.__dict__ or Path(inspect.getfile(function)).resolve()!=path.resolve()):
        raise ValueError('Invalid source function binding')
    original=ast.parse(inspect.getsource(function));changed=copy.deepcopy(original)
    assignments={name:[] for name in ('center','drift')}
    for node in ast.walk(changed):
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            name=node.targets[0].id
            if name in assignments:assignments[name].append(node)
    if any(len(v)!=1 for v in assignments.values()):raise ValueError('Unexpected frame assignment structure')
    namespace=module.__dict__.copy()
    if vectors is not None:
        for name,array in zip(('center','drift'),vectors):
            variable='_diagnostic_fixed_'+name;namespace[variable]=array
            assignments[name][0].value=ast.parse(variable+'.copy()',mode='eval').body
    # Independently mask only the two allowed values and compare the full AST.
    def masked(tree):
        tree=copy.deepcopy(tree)
        for node in ast.walk(tree):
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in assignments:
                node.value=ast.Constant(None)
        return ast.dump(tree,include_attributes=False)
    if masked(original)!=masked(changed):raise ValueError('Unexpected diagnostic source difference')
    ast.fix_missing_locations(changed)
    exec(compile(changed,'<q2-frame393-trusted-source>','exec'),namespace)
    result=namespace['integrate']
    result.diagnostic_origin=dict(source_SHA256=SOURCE_SHA256,replaced_assignments=[] if vectors is None else ['center','drift'],
        mathematical_model_changed=False,solver_is_cold=True,source_AST_otherwise_identical=True)
    return result
