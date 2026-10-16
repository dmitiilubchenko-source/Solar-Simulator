"""Membership edits and full many-body 1PN terms without JPL assumptions."""
import numpy as np
import pytest

from scripts.edited_j2_three import CASES,fixture,snapshot_controls
from scripts.edited_j2 import verify_branch
from scripts.fixed_j2_ias import entries,figure_force,potential
from scripts.eih_year import force_terms
from scripts.assess_sandbox_planets import states
from solar_simulator.native_forces import prepare as native_prepare
from solar_simulator.oblateness import acceleration,prepare
from solar_simulator.relativity import C,eih_acceleration
from solar_simulator.simulation import G
from solar_simulator.storage import to_document


@pytest.mark.parametrize('case',CASES)
def test_membership_edit_preserves_unedited_states_and_parent(case):
    parent,branch,times,period=fixture(case);before=to_document(parent)
    verify_branch(parent,branch)
    assert parent.time==(0 if case=='add_start' else period/4)
    assert len(branch.child.bodies)==(2 if case=='remove_quarter' else 3)
    before_by_name={b.name:row for b,row in zip(parent.bodies,states(parent.bodies))}
    for body,row in zip(branch.child.bodies,states(branch.child.bodies)):
        if body.name in before_by_name:np.testing.assert_array_equal(row,before_by_name[body.name])
    assert branch.child.origin is None and branch.child.time==0
    assert to_document(parent)==before and to_document(branch.parent)==before
    assert len(times)==61 and times[-1]==2*period
    assert snapshot_controls(branch.child)['checks_passed']


@pytest.mark.parametrize('case',['add_start','mass_quarter'])
def test_full_three_body_pn_is_not_a_sum_of_isolated_pairs(case):
    _,branch,_,_=fixture(case);seed=branch.child
    q=states(seed.bodies);m=np.array([b.mass for b in seed.bodies]);p,v=q[:,:3],q[:,3:]
    newton,pn=force_terms(p,v,G*m,C);native=native_prepare(m)
    for actual in (native(p,v,C)-native(p,v),eih_acceleration(p,v,m)-newton):
        assert np.linalg.norm(actual-pn,axis=1).max()/np.linalg.norm(pn,axis=1).max()<3e-9
    pair_only=np.zeros_like(pn)
    for i in range(3):
        for j in range(i+1,3):
            _,pair=force_terms(p[[i,j]],v[[i,j]],G*m[[i,j]],C)
            pair_only[i]+=pair[0];pair_only[j]+=pair[1]
    assert np.linalg.norm(pair_only-pn,axis=1).max()/np.linalg.norm(pn,axis=1).max()>1e-4


@pytest.mark.parametrize('case',['add_start','mass_quarter'])
def test_three_body_figure_gradient_reaction_and_covariance(case):
    _,branch,_,_=fixture(case);seed=branch.child
    q=states(seed.bodies);p=q[:,:3];m=np.array([b.mass for b in seed.bodies]);fig=entries(seed)
    expected=figure_force(p,m,fig);scale=np.linalg.norm(expected,axis=1).max()
    actual=acceleration(p,m,prepare(seed.bodies,seed.settings.figures))
    assert np.linalg.norm(actual-expected,axis=1).max()/scale<5e-13
    for i in range(3):
        for k in range(3):
            probe=p.astype(complex);probe[i,k]+=1e-12j
            assert abs(expected[i,k]+potential(probe,m,fig).imag/1e-12/m[i])/scale<5e-13
    forces=m[:,None]*expected
    assert np.linalg.norm(forces.sum(axis=0))/np.linalg.norm(forces,axis=1).sum()<5e-13
    missing=forces.copy();missing[0]=0.
    assert np.linalg.norm(missing.sum(axis=0))/np.linalg.norm(forces,axis=1).sum()>1e-3
    rotation=np.array([[0.,-1.,0.],[.6,0.,-.8],[.8,0.,.6]])
    moved=tuple((i,r,rotation@tensor@rotation.T) for i,r,tensor in fig)
    transformed=figure_force(p@rotation.T+np.array([2e8,-1e8,3e8]),m,moved)
    assert np.linalg.norm(transformed-expected@rotation.T,axis=1).max()/scale<5e-13
