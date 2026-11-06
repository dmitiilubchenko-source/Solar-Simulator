"""Independent saved-state observer arithmetic and invalid-input checks."""
import pytest

def test_independent_angle_uses_relative_quaternion_and_sign_equivalence():
    import math
    from scripts.q2_frame_observer393 import orientation_angle
    q=[1.,5e-16,0.,0.]
    assert orientation_angle([1.,0.,0.,0.],q)==pytest.approx(2*math.atan(5e-16),rel=2e-15,abs=0)
    assert orientation_angle(q,[-x for x in q])==0
    with pytest.raises(ValueError):orientation_angle([0.]*4,q)


@pytest.mark.parametrize('scale',[1e300,1e-300])
def test_angle_is_stable_for_extreme_finite_quaternion_scales(scale):
    import math
    from scripts.q2_frame_observer393 import orientation_angle
    x=scale*5e-16
    assert orientation_angle([scale,0.,0.,0.],[scale,x,0.,0.])==pytest.approx(2*math.atan(x/scale),rel=2e-15,abs=0)


def test_independent_invariants_have_analytic_single_rigid_body_limit():
    from scripts.q2_frame_observer393 import invariants
    from decimal import Decimal
    doc=dict(settings=dict(physics='newtonian',figures=[]),bodies=[dict(name='A',mass=2.)],
        rotations=[dict(body='A',figure=dict(mass=2.,moments=[2.,2.,2.]))])
    state=dict(positions=[[0.,1.,0.]],velocities=[[1.,0.,0.]],quaternions=[[1.,0.,0.,0.]],spins=[[0.,0.,4.]])
    r=invariants(state,doc,1.)
    assert Decimal(r['E_J'])==5 and [Decimal(x) for x in r['P_kg_m_s']]==[2,0,0]
    assert [Decimal(x) for x in r['L_kg_m2_s']]==[0,0,2]


@pytest.mark.parametrize('change',['mass_bool','nan_position','shape','zero_q','negative_I','unsupported_model'])
def test_independent_observer_rejects_invalid_inputs(change):
    from scripts.q2_frame_observer393 import invariants
    doc=dict(settings=dict(physics='newtonian',figures=[]),bodies=[dict(name='A',mass=2.)],
        rotations=[dict(body='A',figure=dict(mass=2.,moments=[2.,2.,2.]))])
    state=dict(positions=[[0.,1.,0.]],velocities=[[1.,0.,0.]],quaternions=[[1.,0.,0.,0.]],spins=[[0.,0.,4.]])
    if change=='mass_bool':doc['bodies'][0]['mass']=True
    if change=='nan_position':state['positions'][0][0]=float('nan')
    if change=='shape':state['velocities'][0]=[0.]
    if change=='zero_q':state['quaternions'][0]=[0.]*4
    if change=='negative_I':doc['rotations'][0]['figure']['moments'][0]=-1.
    if change=='unsupported_model':doc['settings']['physics']='eih-1pn'
    with pytest.raises(ValueError):invariants(state,doc,1.)


def test_pair_differences_preserve_sign_equivalence_and_inputs():
    from scripts.q2_frame_observer393 import differences
    import copy
    doc=dict(settings=dict(physics='newtonian',figures=[]),bodies=[dict(name='A',mass=1.),dict(name='B',mass=1.)],
        rotations=[dict(body='A',figure=dict(mass=1.,moments=[1.,1.,1.]))])
    a=dict(positions=[[0.,0.,0.],[2.,0.,0.]],velocities=[[0.,0.,0.],[0.,0.,0.]],quaternions=[[1.,0.,0.,0.]],spins=[[0.,0.,0.]])
    b=copy.deepcopy(a);b['quaternions'][0][0]=-1.;before=copy.deepcopy((a,b))
    r=differences(a,b,doc,1.)
    assert r['raw_quaternion']==[2.] and r['sign_aligned_raw_quaternion']==[0.] and r['orientation_angle_rad']==[0.]
    assert r['E_difference_J']==0 and r['relative_positions']==0 and (a,b)==before


@pytest.mark.parametrize('precision',[True,0,49,301,80.])
def test_observer_precision_is_explicitly_bounded(precision):
    from scripts.q2_frame_observer393 import orientation_angle
    with pytest.raises(ValueError):orientation_angle([1.,0.,0.,0.],[1.,0.,0.,0.],precision)
