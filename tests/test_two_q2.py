"""418 product boundary. Original tests preserved in product-before418-tests.zip.
Historical scientific arrays/FAIL are audited by test_two_q2_evidence.py.
"""
import numpy as np
import pytest
from scripts.two_q2_fixture380 import fixture
from solar_simulator.experiment import create_experiment,advance


@pytest.mark.parametrize("third",[False,True])
def test_current_product_refuses_two_figures(third):
    b,r,s=fixture(third)
    with pytest.raises(ValueError,match="не более одного"):
        create_experiment(b,s,rotations=r)


def test_each_single_figure_remains_supported():
    from solar_simulator.storage import to_document,from_document
    b,r,s=fixture()
    for rotation in r:
        initial=create_experiment(b,s,rotations=(rotation,))
        final=advance(initial,1)
        assert len(final.rotations)==1 and final.time==50
        assert to_document(from_document(to_document(final)))==to_document(final)
        assert initial.rotations==(rotation,)


def test_single_spin_error_is_not_diluted_by_other_bodies():
    from solar_simulator.nbody_rotation import RotationDOP853
    values=[]
    for n in (2,100):
        y=np.zeros(6*n+7);y[6*n]=1
        solver=RotationDOP853(lambda t,y:np.zeros_like(y),0.,y,1.,body_count=n,rotation_count=1)
        k=np.zeros((len(solver.E5),len(y)));k[0,-1]=2
        values.append(solver._estimate_error_norm(k,.2,np.ones_like(y)))
    assert values[0]>0 and values[0]==values[1]
