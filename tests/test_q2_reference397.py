"""Output-only checks: synthetic solution.y, no RK45 integrations in tests."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import q2_reference397 as new,two_q2_reference380 as old
from scripts.two_q2_fixture380 import fixture
from solar_simulator.experiment import create_experiment
from solar_simulator.storage import to_document


def document(K=2,third=False):
    b,r,s=fixture(third)
    return to_document(create_experiment(b,s,rotations=r[:K]))


def capture(monkeypatch,module,doc,values=None):
    saved={}
    def solve(rhs,span,initial,**kwargs):
        y=np.tile(initial[:,None],(1,len(kwargs['t_eval']))) if values is None else values
        saved.update(initial=initial.copy(),rhs=rhs,kwargs=kwargs)
        return SimpleNamespace(success=True,y=y,t=np.array(kwargs['t_eval']),nfev=0)
    monkeypatch.setattr(module,'solve_ivp',solve)
    result=module.reference(doc,[0.,.001],3e-11)
    return result,saved


def test_unchanged_entire_preparation_rhs_and_solver_call():
    def prefix(module):
        tree=ast.parse(Path(module.__file__).read_bytes());fn=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='reference')
        index=next(i for i,x in enumerate(fn.body) if isinstance(x,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='solution' for t in x.targets))
        return [ast.dump(x,include_attributes=False) for x in fn.body[:index+1]]
    assert prefix(new)==prefix(old)


@pytest.mark.parametrize('third',[False,True])
@pytest.mark.parametrize('reverse',[False,True])
def test_k2_output_bytes_same_on_same_y(monkeypatch,third,reverse):
    doc=document(2,third)
    if reverse:doc['bodies'].reverse();doc['rotations'].reverse()
    before=deepcopy(doc);a,context=capture(monkeypatch,old,doc)
    values=np.tile(context['initial'][:,None],(1,2))
    # Finite off-manifold data make a hidden orthogonal projection observable.
    values[6*len(doc['bodies']),1]+=1e-7
    a,_=capture(monkeypatch,old,doc,values);b,_=capture(monkeypatch,new,doc,values)
    for key in ('positions','velocities','orientation','spins'):assert a[key].shape==b[key].shape and a[key].tobytes()==b[key].tobytes()
    assert a['RHS']==b['RHS']==0 and doc==before


@pytest.mark.parametrize('body_index',[0,1])
def test_k1_reconstruction_and_body_order(monkeypatch,body_index):
    doc=document();doc['rotations']=[doc['rotations'][body_index]];before=deepcopy(doc)
    result,context=capture(monkeypatch,new,doc)
    assert len(context['initial'])==6*len(doc['bodies'])+12
    assert result['orientation'].shape==(2,1,3,3) and result['spins'].shape==(2,1,3)
    from scipy.spatial.transform import Rotation
    expected=Rotation.from_quat(np.roll(doc['rotations'][0]['quaternion'],-1)).as_matrix()
    assert np.array_equal(result['orientation'][0,0],expected)
    for key,expected_values in [('positions',[b['position'] for b in doc['bodies']]),('velocities',[b['velocity'] for b in doc['bodies']]),('spins',[doc['rotations'][0]['angular_momentum']])]:
        x=np.array(expected_values);assert np.max(np.abs(result[key][0]-x))<=8*np.finfo(float).eps*np.linalg.norm(x)
    assert doc==before
    with pytest.raises(ValueError,match='reshape'):capture(monkeypatch,old,doc)


@pytest.mark.parametrize('fault',['rows','columns','float32','bool','nan','infinity','epochs','failed','K0','K3','duplicate-body','unknown-source','duplicate-source','mass','scales'])
def test_corrupt_outputs_rejected_without_mutation(monkeypatch,fault):
    doc=document();_,context=capture(monkeypatch,new,doc)
    N=len(doc['bodies']);y=np.tile(context['initial'][:,None],(1,2));times=np.array([0.,.001]);scales=[1.,1.]
    solution=SimpleNamespace(success=True,y=y,t=times.copy(),nfev=0)
    if fault=='rows':solution.y=y[:-1]
    elif fault=='columns':solution.y=y[:,:1]
    elif fault=='float32':solution.y=y.astype(np.float32)
    elif fault=='bool':solution.y=y.astype(bool)
    elif fault=='nan':solution.y[0,0]=np.nan
    elif fault=='infinity':solution.y[0,0]=np.inf
    elif fault=='epochs':solution.t=np.array([0.,.002])
    elif fault=='failed':solution.success=False
    elif fault=='K0':doc['rotations']=[]
    elif fault=='K3':doc['rotations'].append(deepcopy(doc['rotations'][0]))
    elif fault=='duplicate-body':doc['bodies'][1]['name']=doc['bodies'][0]['name']
    elif fault=='unknown-source':doc['rotations'][0]['body']='absent'
    elif fault=='duplicate-source':doc['rotations'][1]['body']=doc['rotations'][0]['body']
    elif fault=='mass':doc['rotations'][0]['figure']['mass']*=2
    elif fault=='scales':scales[0]=np.inf
    original=solution.y.tobytes();before=deepcopy(doc)
    with pytest.raises(ValueError):new.unpack_solution(solution,doc,times,np.zeros(3),np.zeros(3),1.,1.,scales)
    assert solution.y.tobytes()==original and doc==before
