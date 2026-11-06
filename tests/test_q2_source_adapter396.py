"""Fault checks and a synthetic, no-integration reproducer of K=1 preflight."""
from copy import deepcopy
from types import SimpleNamespace
import json

import numpy as np
import pytest

from scripts import q2_source_adapter396 as a


def test_source_and_environment_rejection(tmp_path):
    path=tmp_path/'source';path.write_bytes(b'original')
    a.require_sha(path,a.sha(path))
    with pytest.raises(ValueError,match='SHA'):a.require_sha(path,'0'*64)
    a.require_environment({'source':'new'},{'source':'new'})
    with pytest.raises(ValueError,match='environment'):a.require_environment({'source':'dev'},{'source':'new'})
    assert path.read_bytes()==b'original'


def test_origins(tmp_path):
    root=tmp_path/'candidate';env=tmp_path/'env';package=root/'src'/'solar_simulator'/'__init__.py'
    a.require_origins(package,[env/'numpy.py',env/'native.pyd'],root,env,env)
    with pytest.raises(ValueError,match='source'):a.require_origins(tmp_path/'dev/src/init.py',[],root,env,env)
    with pytest.raises(ValueError,match='dependency'):a.require_origins(package,[tmp_path/'other/native.pyd'],root,env,env)
    with pytest.raises(ValueError,match='interpreter'):a.require_origins(package,[],root,env,tmp_path/'other')


def test_output_exclusive(tmp_path):
    out=tmp_path/'new';a.new_output(out)
    with pytest.raises(FileExistsError):a.new_output(out)
    assert list(out.iterdir())==[]


def test_result_roundtrip_and_owner(tmp_path):
    p=tmp_path/'result.json';binding={'commit':'candidate','input_SHA256':'fixed','environment':'new'}
    meta=a.save_result(p,{'rawq':[1.,0.,0.,0.],'time':50.},binding)
    before={x.name:x.read_bytes() for x in tmp_path.iterdir()}
    assert a.read_result(p,binding)['time']==50. and meta['sha256']==a.sha(p)
    with pytest.raises(ValueError,match='binding'):a.read_result(p,{**binding,'commit':'dev'})
    with pytest.raises(FileExistsError):a.save_result(p,{},binding)
    assert before=={x.name:x.read_bytes() for x in tmp_path.iterdir()}


@pytest.mark.parametrize('fault',['no-sidecar','bad-sha','payload','sidecar-only'])
def test_incomplete_or_corrupt_never_reused(tmp_path,fault):
    p=tmp_path/'result.json';b={'commit':'candidate'};a.save_result(p,{},b);sidecar=p.with_suffix('.json.sha256.json')
    if fault=='no-sidecar':sidecar.unlink()
    elif fault=='bad-sha':
        x=json.loads(sidecar.read_bytes());x['sha256']='0'*64;sidecar.write_text(json.dumps(x))
    elif fault=='payload':p.write_bytes(p.read_bytes().replace(b'candidate',b'other0000'))
    else:p.unlink()
    before={x.name:x.read_bytes() for x in tmp_path.iterdir()}
    with pytest.raises(ValueError):a.read_result(p,b)
    with pytest.raises(FileExistsError):a.save_result(p,{},b)
    assert before=={x.name:x.read_bytes() for x in tmp_path.iterdir()}


def test_historical_reference_k1_unpack_reproducer(monkeypatch):
    from scripts import two_q2_reference380 as old
    from scripts.two_q2_fixture380 import fixture
    from solar_simulator.experiment import create_experiment
    from solar_simulator.storage import to_document
    bodies,rotations,settings=fixture();doc=to_document(create_experiment(bodies,settings,rotations=rotations[:1]))
    before=deepcopy(doc);captured={}
    def exact_zero_step(rhs,span,initial,**kwargs):
        captured['dimension']=len(initial)
        return SimpleNamespace(success=True,y=np.tile(initial[:,None],(1,2)),nfev=0)
    monkeypatch.setattr(old,'solve_ivp',exact_zero_step)
    with pytest.raises(ValueError,match='reshape'):old.reference(doc,[0.,.001],3e-11)
    assert captured['dimension']==6*len(bodies)+12 and doc==before
    # Same unchanged unpacker accepts two figures. This is shape/initial-epoch
    # arithmetic, not an RK45 trajectory or a qualification PASS.
    doc2=to_document(create_experiment(bodies,settings,rotations=rotations))
    result=old.reference(doc2,[0.,.001],3e-11);a.require_reference_shape(result,doc2,[0.,.001])
    assert result['RHS']==0


def test_reference_shape_rejects_extra_spin():
    document={'bodies':[{},{}],'rotations':[{}]};times=[0.,1.]
    result=dict(positions=np.zeros((2,2,3)),velocities=np.zeros((2,2,3)),orientation=np.zeros((2,1,3,3)),spins=np.zeros((2,1,3)))
    a.require_reference_shape(result,document,times)
    result['spins']=np.zeros((2,2,3))
    with pytest.raises(ValueError,match='shape'):a.require_reference_shape(result,document,times)
