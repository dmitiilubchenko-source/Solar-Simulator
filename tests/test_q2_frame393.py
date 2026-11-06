"""Frame diagnostic safety, noninterference and unchanged solver path."""
import types
import numpy as np
import pytest
from scripts.q2_fixed_frame393 import clone_integrate
from solar_simulator import nbody_rotation as nr


@pytest.mark.parametrize('value',[[True,0.,0.],[float('nan'),0.,0.],[float('inf'),0.,0.],['1',0.,0.],[1.,2.],[10**400,0.,0.],np.zeros(3)])
def test_invalid_frame_is_rejected_before_any_solve(value):
    with pytest.raises(ValueError):clone_integrate(nr,center=value,drift=[0.,0.,0.])


def test_partial_frame_and_untrusted_source_are_rejected(tmp_path):
    with pytest.raises(ValueError):clone_integrate(nr,center=[0.,0.,0.])
    m=types.ModuleType('changed');p=tmp_path/'changed.py';p.write_text('pass');m.__file__=str(p)
    with pytest.raises(ValueError,match='SHA'):clone_integrate(m)


def test_owned_frame_and_exactly_two_substitutions():
    center=[1.,2.,3.];f=clone_integrate(nr,center=center,drift=[.1,.2,.3]);center[0]=999.
    assert f.__globals__['_diagnostic_fixed_center'].tolist()==[1.,2.,3.]
    assert not f.__globals__['_diagnostic_fixed_center'].flags.writeable
    assert f.diagnostic_origin['replaced_assignments']==['center','drift']
    assert f.diagnostic_origin['source_AST_otherwise_identical']
    assert nr.integrate is not f


def test_disabled_frame_clone_matches_original_numbers_exactly():
    from scripts.two_q2_fixture380 import fixture
    bodies,rotations,_=fixture();f=clone_integrate(nr)
    before=nr.integrate
    a=before(bodies,rotations,[0.,.125],relative_pair=('A','B'))
    b=f(bodies,rotations,[0.,.125],relative_pair=('A','B'))
    def numbers(samples):
        return np.array([[v for body in bs for vec in (body.position,body.velocity) for v in (vec.x,vec.y,vec.z)]
            +[v for r in rs for vec in (r.quaternion,r.angular_momentum) for v in vec] for bs,rs in samples])
    assert numbers(a).tobytes()==numbers(b).tobytes()
    assert nr.integrate is before and f.diagnostic_origin['replaced_assignments']==[]
