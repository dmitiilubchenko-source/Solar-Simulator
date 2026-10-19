"""Algebraic checks for tiny sources without rounded total accelerations."""
from decimal import Decimal,localcontext

import numpy as np
import pytest

from scripts.noether_identities import (convert,parts,forces,response,direction,plus,dec,
    snapshot,precision_agreement,score)
from scripts.decimal_noether import quantities
from scripts.fixed_j2_year import inputs
from scripts.fixed_j2_ias import entries,figure_force,pn_response
from scripts.eih_year import force_terms
from scripts.assess_sandbox_planets import states
from solar_simulator.simulation import G
from solar_simulator.relativity import C


def test_sum_of_separate_parts_matches_frozen_decimal_noether_readout():
    seed,*_=inputs();q=states(seed.bodies);m=[b.mass for b in seed.bodies];fig=entries(seed)
    expected=quantities(q,m,fig)
    with localcontext() as context:
        context.prec=90
        p,v,mm,ff=convert(q,m,fig);result=parts(p,v,mm,ff,dec(G),dec(C))
        actual=plus(*(result[k] for k in ('newton','pn','figure')))
        scale=max(abs(x) for x in expected)
        assert max(abs(a-b)/scale for a,b in zip(actual,expected))<Decimal('1e-60')


def test_scalar_decimal_newton_pair_is_analytic_and_has_full_reaction():
    with localcontext() as context:
        context.prec=70
        p,v,m,f=convert([[-1.,0.,0.,0.,0.,0.],[1.,0.,0.,0.,0.,0.]],[2.,1.],())
        newton,_,_=forces(p,v,m,f,Decimal(1),Decimal(1000))
        assert newton==[[Decimal('.25'),Decimal(0),Decimal(0)],[-Decimal('.5'),Decimal(0),Decimal(0)]]
        assert plus(*[[a*x for x in b] for a,b in zip(m,newton)])==[Decimal(0)]*3


def test_direction_preserves_decimal_velocity_perturbations_far_below_float_ulp():
    with localcontext() as context:
        context.prec=70
        p,v,m,f=convert([[1e12,2e12,-3e12,1e4,-2e4,3e4]],[2.],())
        zero=[[Decimal(0)]*3];dv=[[Decimal('1e-25'),Decimal(0),Decimal(0)]]
        result=direction(p,v,m,f,dec(G),dec(C),'newton',zero,dv,Decimal('1e-7'))
        assert result[1]==Decimal('2e-25')
        assert result[0]==Decimal('2e-21')


def test_separate_decimal_forces_and_hessian_match_existing_scalar_formulas():
    seed,*_=inputs();q=states(seed.bodies);m=np.array([b.mass for b in seed.bodies]);fig=entries(seed)
    with localcontext() as context:
        context.prec=70
        p,v,mm,ff=convert(q,m,fig)
        nn,pn,aq=forces(p,v,mm,ff,dec(G),dec(C))
        analytic=response(p,v,mm,pn,dec(G),dec(C))
    nn,pn,aq=[np.array([[float(x) for x in row] for row in a]) for a in (nn,pn,aq)]
    n0,p0=force_terms(q[:,:3],q[:,3:],G*m,C)
    for a,b in ((nn,n0),(pn,p0),(aq,figure_force(q[:,:3],m,fig))):
        assert np.linalg.norm(a-b,axis=1).max()/np.linalg.norm(a,axis=1).max()<5e-13
    h=pn_response(q[:,:3],q[:,3:],m,pn)
    analytic=np.array([[float(x) for x in row] for row in analytic])
    assert np.linalg.norm(h-analytic,axis=1).max()/np.linalg.norm(analytic,axis=1).max()<5e-13


def test_zero_signal_does_not_acquire_an_epsilon_denominator():
    z=[Decimal(0)]*7
    assert score(z,z,[Decimal(0)]*3,Decimal('1e-8'))['checks_passed']
    bad=z.copy();bad[0]=Decimal('1e-80')
    row=score(bad,z,[Decimal(0)]*3,Decimal('1e-8'))
    assert not row['checks_passed'] and row['blocks']['energy']['scaled_error'] is None


@pytest.mark.parametrize('precision',[50,80,True])
def test_undeclared_precision_is_rejected(precision):
    with pytest.raises(ValueError,match='precision'):snapshot([[0.,0.,0.,0.,0.,0.]],[1.],(),precision)


@pytest.fixture(scope='module')
def initial_identities():
    seed,*_=inputs();q=states(seed.bodies);m=[b.mass for b in seed.bodies];fig=entries(seed)
    return snapshot(q,m,fig,70),snapshot(q,m,fig,90)


def test_initial_ten_body_identities_and_precision_refinement(initial_identities):
    low,high=initial_identities
    assert low['checks_passed'] and high['checks_passed']
    assert precision_agreement(low,high)['checks_passed']


def test_initial_negative_controls_are_detectable(initial_identities):
    row=initial_identities[1]['levels'][-1]['negative_controls']
    assert row['missing_reaction_defect']>1e-3
    assert row['missing_static_energy_defect']>1e-3
    assert row['pair_only_pn_defect']>1e-6
    for blocks in row['omitted_sources'].values():
        assert all(x is None or x>.9 for x in blocks.values())
