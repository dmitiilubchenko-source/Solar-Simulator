"""Numerically resolvable orientation and archived-state metric contracts."""
import math
import numpy as np
import pytest
from scripts.q2_saved_metrics392 import orientation_arithmetic,exact_norm_difference,compare,audit_saved


def test_tiny_physical_angle_survives_trace_acos_cancellation():
    q=[1.,5e-16,0.,0.];I=np.eye(3).ravel()
    value=orientation_arithmetic([1.,0.,0.,0.],q,I,I)
    assert value['angle_rad']==pytest.approx(2*math.atan(5e-16),rel=2e-15,abs=0)
    assert value['matrix_frobenius_from_q']==pytest.approx(math.sqrt(2)*1e-15,rel=2e-15,abs=0)
    assert math.acos((np.trace(np.eye(3))-1)/2)==0


def test_quaternion_sign_does_not_change_physical_orientation():
    q=[1.,.2,-.3,.4];I=np.eye(3).ravel()
    value=orientation_arithmetic(q,[-x for x in q],I,I)
    assert value['angle_rad']==0
    assert value['matrix_frobenius_from_q']==0


def test_scaled_quaternion_comparison_respects_decimal_resolution():
    q=[1.,.2,-.3,.4];I=np.eye(3).ravel()
    from fractions import Fraction
    a=[Fraction.from_float(x) for x in q];b=[-2*x for x in a]
    aa=sum(x*x for x in a);bb=sum(x*x for x in b)
    assert all(x*y/aa==u*v/bb for x,u in zip(a,b) for y,v in zip(a,b))
    value=orientation_arithmetic(q,[-2*x for x in q],I,I,precision=70)
    # Finite Decimal divisions need not cancel exactly after power-of-two scaling.
    # 70 significant digits with >60 bounded operations: 1000 ulps at scale1.
    assert value['angle_rad']<1e-67
    assert value['matrix_frobenius_from_q']<1e-67


def test_exact_binary64_norm_retains_adjacent_float_difference():
    x=1.;y=math.nextafter(x,math.inf)
    assert exact_norm_difference([x,0.,0.],[y,0.,0.])==y-x


def test_zero_quaternion_is_rejected_by_independent_observer():
    with pytest.raises(ValueError):orientation_arithmetic([0.]*4,[1.,0.,0.,0.],np.eye(3).ravel(),np.eye(3).ravel())


def test_body_spin_scales_and_epoch_location_remain_separate():
    d=dict(bodies=[dict(name='A',position=[0.,0.,0.],velocity=[0.,0.,0.]),dict(name='B',position=[10.,0.,0.],velocity=[2.,0.,0.])],
        rotations=[dict(body='A',angular_momentum=[100.,0.,0.]),dict(body='B',angular_momentum=[1.,0.,0.])])
    a=dict(positions=np.zeros((2,2,3)),velocities=np.zeros((2,2,3)),orientation=np.tile(np.eye(3),(2,2,1,1)),spins=np.zeros((2,2,3)))
    b={k:v.copy() for k,v in a.items()};b['positions'][1,1,0]=1.;b['spins'][1,1,2]=.2
    result=compare(a,b,d,[0.,5.])
    assert result['position']['maximum']['value']==.1
    assert result['spin']['maximum']['value']==.2
    assert result['spin']['maximum']['body']=='B' and result['spin']['maximum']['time_seconds']==5.


def test_pinned_saved_audit_recomputes_all_four_without_hiding_failures():
    from pathlib import Path
    result=audit_saved(Path(__file__).resolve().parents[1])
    assert len(result['rows'])==4 and result['numerical_integrations']==0
    assert [r['original_criterion_pass'] for r in result['rows']]==[False,False,False,True]


def test_pinned_audit_rejects_changed_input_before_loading_arrays(tmp_path):
    p=tmp_path/'scripts/two-q2-380-completion-plan.json';p.parent.mkdir();p.write_text('{}')
    with pytest.raises(ValueError,match='SHA mismatch'):audit_saved(tmp_path)


def test_cli_existing_output_is_never_overwritten(tmp_path,monkeypatch):
    from scripts.q2_saved_metrics392 import main
    import sys
    p=tmp_path/'kept.json';p.write_bytes(b'original')
    monkeypatch.setattr(sys,'argv',['q2_saved_metrics392','--root',str(tmp_path/'absent'),'--output',str(p)])
    with pytest.raises(FileExistsError):main()
    assert p.read_bytes()==b'original'
