"""Analytic readout checks independent of trajectory integration and float subtraction."""
from decimal import Decimal,localcontext

import numpy as np
import pytest

from scripts.decimal_noether import quantities,exact,compare_readouts
from scripts.fixed_j2_year import inputs
from scripts.fixed_j2_ias import entries,quantities as old_quantities,scales
from scripts.assess_sandbox_planets import states


def test_exact_conversion_preserves_binary_inputs_instead_of_decimal_spelling():
    assert exact(.1) == Decimal.from_float(.1) and exact(.1) != Decimal('0.1')


def test_one_free_body_analytic_energy_momentum_and_angular_momentum():
    state = np.array([[2.,3.,4.,.1,.2,.3]])
    result = quantities(state,[2.],g=0.,c=1000.)
    with localcontext() as ctx:
        ctx.prec = 70
        p = list(map(exact,state[0,:3]));v = list(map(exact,state[0,3:]))
        speed = sum(x*x for x in v)
        momentum = [2*x*(1+speed/(2*Decimal(1000)**2)) for x in v]
        expected = tuple([speed+Decimal(3)*speed**2/(4*Decimal(1000)**2),*momentum,
            *(p[(k+1)%3]*momentum[(k+2)%3]-p[(k+2)%3]*momentum[(k+1)%3] for k in range(3))])
        assert max(abs(a-b) for a,b in zip(result,expected)) < Decimal('1e-65')


def test_ten_body_analytic_readout_agrees_with_independent_scalar_action():
    seed,*_ = inputs();q = states(seed.bodies);m = [b.mass for b in seed.bodies];fig = entries(seed)
    scale = scales(q,np.array(m),fig,seed.settings.physics)
    high = quantities(q,m,fig)
    old = old_quantities(q,np.array(m),fig,seed.settings.physics)
    assert max(abs(float(a)-b)/s for a,b,s in zip(high,old,scale)) < 5e-13
    low = quantities(q,m,fig,precision=50)
    with localcontext() as ctx:
        ctx.prec = 80
        assert max(abs(float((a-b)/exact(s))) for a,b,s in zip(high,low,scale)) < 1e-40


def test_constant_stored_state_has_exact_zero_decimal_changes_without_reintegrating():
    q = np.array([[-1.,0.,0.,0.,.1,0.],[1.,0.,0.,0.,-.2,0.]])
    values = np.tile(q,(3,1,1));m = np.array([2.,1.]);budget = np.zeros((3,3,7))
    old = np.tile(np.array(list(map(float,quantities(q,m)))),(3,1))
    row,arrays = compare_readouts(values,budget,m,(),np.ones(7),old)
    assert row['precision_checks_passed'] and not row['trajectories_reintegrated']
    assert not row['full_source_observability_qualified']
    assert np.array_equal(arrays['decimal_residual'],np.zeros((3,7)))


@pytest.mark.parametrize('precision',[True,20,3.5])
def test_invalid_precision_is_rejected(precision):
    with pytest.raises(ValueError):quantities([[0.,0.,0.,1.,0.,0.]],[1.],precision=precision)


def test_coincident_bodies_are_rejected_without_softening():
    with pytest.raises(ValueError,match='Coincident'):quantities(np.zeros((2,6)),[1.,2.])
