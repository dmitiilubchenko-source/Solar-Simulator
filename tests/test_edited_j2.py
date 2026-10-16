"""Actual child IC, force separation, budget units and legacy continuation."""
from math import sqrt

import numpy as np
import pytest

from scripts.edited_j2 import (CASES,fixture,verify_branch,variants,legacy_trajectory,
    checkpoint_check,reference_gate,metrics)
from scripts.fixed_j2_ias import (entries,figure_force,potential,full_force,reference,
    sources,scales,dop_trajectory,model)
from scripts.eih_year import force_terms
from scripts.assess_sandbox_planets import states
from solar_simulator.experiment import reset
from solar_simulator.native_forces import prepare as native_prepare
from solar_simulator.oblateness import acceleration,prepare
from solar_simulator.relativity import C,eih_acceleration
from solar_simulator.simulation import G
from solar_simulator.storage import to_document


@pytest.mark.parametrize('case',CASES)
def test_only_declared_parameter_changes_without_recentring(case):
    parent,branch,times,period=fixture(case);before=to_document(parent)
    metadata=verify_branch(parent,branch)
    p,q=states(parent.bodies),states(branch.child.bodies)
    action=case.split('_')[0]
    assert branch.child.settings==parent.settings and branch.child.origin is None
    assert parent.time==(0 if case.endswith('start') else period/4)
    assert metadata['parent_time_seconds']==parent.time and len(metadata['changes'])==1
    assert np.array_equal(times,np.linspace(0,2*period,61))
    if action=='mass':
        np.testing.assert_array_equal(p,q)
        assert branch.child.bodies[0].mass==parent.bodies[0].mass*1.25
    else:
        assert [b.mass for b in parent.bodies]==[b.mass for b in branch.child.bodies]
        np.testing.assert_array_equal(q[0],p[0])
    if action=='position':
        np.testing.assert_array_equal(q[1,:3],p[1,:3]+[3e6,-2e6,4e6])
        np.testing.assert_array_equal(q[:,3:],p[:,3:])
    if action=='velocity':
        np.testing.assert_array_equal(q[:,:3],p[:,:3])
        np.testing.assert_array_equal(q[1,3:],p[0,3:]+.9*(p[1,3:]-p[0,3:]))
    assert to_document(parent)==before and to_document(branch.parent)==before
    assert to_document(reset(branch.child))==to_document(branch.child)


@pytest.mark.parametrize('case',CASES)
def test_child_j2_and_pn_corrections_separately_match_independent_force(case):
    _,branch,_,_=fixture(case);seed=branch.child
    q=states(seed.bodies);m=np.array([b.mass for b in seed.bodies]);p,v=q[:,:3],q[:,3:]
    newton,pn=force_terms(p,v,G*m,C)
    native=native_prepare(m)
    for actual in (native(p,v,C)-native(p,v),eih_acceleration(p,v,m)-newton):
        assert np.linalg.norm(actual-pn,axis=1).max()/np.linalg.norm(pn,axis=1).max()<3e-9
    expected=figure_force(p,m,entries(seed))
    actual=acceleration(p,m,prepare(seed.bodies,seed.settings.figures))
    scale=np.linalg.norm(expected,axis=1).max()
    assert np.linalg.norm(actual-expected,axis=1).max()/scale<5e-13
    gradient=np.zeros_like(p)
    for i in range(len(m)):
        for k in range(3):
            probe=p.astype(complex);probe[i,k]+=1e-12j
            gradient[i,k]=potential(probe,m,entries(seed)).imag/1e-12
    assert np.linalg.norm(expected+gradient/m[:,None],axis=1).max()/scale<5e-13
    np.testing.assert_allclose(full_force(seed)(p,v),newton+pn+expected,rtol=5e-13,atol=1e-12)
    forces=m[:,None]*expected
    assert np.linalg.norm(forces.sum(axis=0))/np.linalg.norm(forces,axis=1).sum()<5e-13


@pytest.mark.parametrize('case',['mass_start','mass_quarter'])
def test_reference_uses_child_mass_clock_and_resets_source_integrals(case):
    parent,branch,_,period=fixture(case);seed=branch.child
    elapsed=period*1e-7;times=np.array([0.,elapsed])
    values,budgets,metadata=reference(seed,times,3e-14,elapsed/2)
    m=np.array([b.mass for b in seed.bodies]);q=states(seed.bodies)
    assert metadata['mass_kg']==sum(m) and metadata['mass_kg']!=sum(b.mass for b in parent.bodies)
    assert metadata['clock_seconds']==sqrt(1e24/(G*sum(m)))
    assert np.linalg.norm(values[0]-q)<1e-6
    np.testing.assert_array_equal(budgets[0],np.zeros((3,7)))
    _,pn=force_terms(q[:,:3],q[:,3:],G*m,C)
    aq=figure_force(q[:,:3],m,entries(seed))
    physical=sources(q[:,:3],q[:,3:],m,pn,aq)
    scale=scales(q,m,entries(seed),seed.settings.physics)
    relative=abs((budgets[-1]/elapsed-physical)/scale).max()/abs(physical/scale).max()
    assert relative<1e-5


@pytest.mark.parametrize('backend',['python','rust'])
def test_legacy_checkpoint_and_packet_times_match_continuous(backend):
    _,branch,_,period=fixture('position_quarter');seed=variants(branch.child)[backend]
    times=np.array([0.,period/100,period/12])
    values,stats=legacy_trajectory(seed,times)
    native=variants(branch.child)['rust']
    continuous,other=dop_trajectory(native,times)
    assert stats['packet_endpoints']==other['packet_endpoints']
    np.testing.assert_array_equal(values[0],states(seed.bodies))
    assert np.linalg.norm(values-continuous,axis=2).max()<.01
    assert checkpoint_check(seed,period/12)


def test_failed_reference_and_inconsistent_arrays_cannot_certify():
    _,branch,_,_=fixture('mass_start');seed=branch.child
    values=np.stack([states(seed.bodies)]*2);budgets=np.zeros((2,3,7))
    row=metrics(values,values,budgets,seed,False)
    assert row['numerical_targets_passed'] and not row['checks_passed']
    for bad in (values[:1],np.full_like(values,np.nan)):
        with pytest.raises(ValueError):metrics(bad,values,budgets,seed,True)
    broken=budgets.copy();broken[-1,0,0]=np.inf
    with pytest.raises(ValueError):reference_gate(values,values,budgets,broken,seed)
    shifted=values.copy();shifted[0,0,0]+=1.
    assert not reference_gate(values,shifted,budgets,budgets,seed)['checks_passed']


def test_storage_boundary_conversion_preserves_historical_model_bits():
    old,_,_=model('eih_two');parent,_,_,_=fixture('mass_start')
    np.testing.assert_array_equal(states(old.bodies),states(parent.bodies))
    assert all(type(v) is float for b in parent.bodies for vector in (b.position,b.velocity)
        for v in (vector.x,vector.y,vector.z))
    assert to_document(parent)['time']==0
