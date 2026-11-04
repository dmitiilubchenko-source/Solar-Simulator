"""Independent checker failure paths, without scientific integrations."""
from copy import deepcopy
import json
import math
import zipfile

import pytest
from scripts.check_compatibility387 import (verify_portable, sha, save, read,
                                            state_bytes, invariants, observe)


def document():
    return dict(time=0.,settings={},initial=[],bodies=[
        dict(name='a',mass=2.,radius=0.,position=[0.,0.,0.],velocity=[0.,1.,0.],spin=[0.,0.,0.]),
        dict(name='b',mass=3.,radius=0.,position=[4.,0.,0.],velocity=[0.,-1.,0.],spin=[0.,0.,0.])])


def test_independent_invariants_analytic_point_pair():
    d=document();actual=invariants(d,1.)
    assert actual==dict(E_J=1.,P_kg_m_s=[0.,-1.,0.],L_kg_m2_s=[0.,0.,-12.])
    assert d==document()


def test_independent_spherical_rotator():
    d=document();d['bodies']=d['bodies'][:1]
    d['rotations']=[dict(body='a',figure=dict(moments=[2.,2.,2.]),quaternion=[1.,0.,0.,0.],angular_momentum=[0.,0.,4.])]
    x=invariants(d,1.)
    assert x['E_J']==5. and x['L_kg_m2_s']==[0.,0.,4.]


def test_mac_cullagh_axis_potential():
    d=document()
    d['rotations']=[dict(body='a',figure=dict(moments=[2.,3.,4.]),quaternion=[1.,0.,0.,0.],angular_momentum=[0.,0.,0.])]
    # base E=1; Q2 correction G*m_b*(3 Ixx-trI)/(2r^3)=-9/128.
    assert invariants(d,1.)['E_J']==1.-9/128


@pytest.mark.parametrize('damage',['archive-sha','member','missing','extra'])
def test_portable_verification_rejects_before_execution(tmp_path,damage):
    directory=tmp_path/'portable';directory.mkdir();(directory/'a.py').write_bytes(b'pass\n')
    archive=tmp_path/'portable.zip'
    with zipfile.ZipFile(archive,'w') as z:z.writestr('portable/a.py',b'pass\n')
    expected=sha(archive)
    if damage=='archive-sha':expected='0'*64
    elif damage=='member':(directory/'a.py').write_bytes(b'fail\n')
    elif damage=='missing':(directory/'a.py').unlink()
    else:(directory/'unexpected.pth').write_bytes(b'unsafe')
    before={p.name:p.read_bytes() for p in directory.iterdir()}
    with pytest.raises(ValueError):verify_portable(archive,directory,expected)
    assert before=={p.name:p.read_bytes() for p in directory.iterdir()}


def test_archive_traversal_rejected(tmp_path):
    d=tmp_path/'portable';d.mkdir();a=tmp_path/'bad.zip'
    with zipfile.ZipFile(a,'w') as z:z.writestr('portable/../outside.py',b'pass')
    with pytest.raises(ValueError,match='Unsafe'):verify_portable(a,d,sha(a))
    assert not (tmp_path/'outside.py').exists()


def test_exclusive_output_and_signed_zero_bits(tmp_path):
    save(tmp_path/'out.json',dict(a=1))
    with pytest.raises(FileExistsError):save(tmp_path/'out.json',dict(a=2))
    assert read(tmp_path/'out.json')==dict(a=1)
    a=document();b=deepcopy(a);b['bodies'][0]['position'][0]=-0.
    assert a==b and state_bytes(a)!=state_bytes(b)


def test_observer_preserves_detectable_difference_and_inputs(tmp_path):
    (tmp_path/'inputs').mkdir()
    save(tmp_path/'plan.json',dict(cases=[dict(id='case',epochs_seconds=[0.,50.,100.,150.])],G_hex=(1.).hex(),inputs_SHA256={}))
    docs=[]
    for t in [0.,50.,100.,150.]:
        d=document();d['time']=t;docs.append(d)
    for label in ('accepted','candidate'):
        folder=tmp_path/label/'case';folder.mkdir(parents=True)
        changed=deepcopy(docs)
        if label=='candidate':changed[-1]['bodies'][0]['position'][2]=1.
        save(folder/'frames.json',changed)
    observe(tmp_path);row=read(tmp_path/'comparison.json')['cases'][0]
    assert row['status']=='UNRESOLVED_DIFFERENCE' and row['max_position_difference_m']==1.
    assert read(tmp_path/'accepted/case/frames.json')==docs
