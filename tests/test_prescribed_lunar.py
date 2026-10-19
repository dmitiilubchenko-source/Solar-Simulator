"""Analytic external-work sign, vector intervention and controlled-evidence guards."""
from copy import deepcopy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from scripts import prescribed_lunar_control as control
from scripts import assess_prescribed_lunar as audit
from scripts.independent_hybrid_rotation import body_field


def test_external_work_and_orbital_torque_match_analytic_triaxial_potential():
    theta,phi,omega=.3,.8,.2
    inertia=np.array([.1,.2,.25]);radius=5.;mass=.2
    r=Rotation.from_rotvec([0.,0.,theta]).as_matrix()
    x=np.array([[0.,0.,0.],[radius*np.cos(phi),radius*np.sin(phi),0.]])
    force,tau_body,u=body_field(x,np.array([1.,mass]),r,inertia,0,1.)
    tau=r@tau_body
    expected_tau=3*mass*(inertia[1]-inertia[0])*np.sin(2*(phi-theta))/(2*radius**3)
    expected_u=mass*(3*(inertia[0]*np.cos(phi-theta)**2+inertia[1]*np.sin(phi-theta)**2)-inertia.sum())/(2*radius**3)
    assert u==pytest.approx(expected_u,rel=3e-15)
    np.testing.assert_allclose(tau,[0.,0.,expected_tau],rtol=2e-15,atol=1e-19)
    source=control.external_source([0.,0.,omega],tau)
    assert source[0]==pytest.approx(-omega*expected_tau,rel=2e-15)
    np.testing.assert_allclose(source[4:],np.cross(x,force).sum(axis=0),rtol=3e-15,atol=1e-19)
    assert abs(source[0])>0 and abs(2*source[0])>abs(source[0])
    np.testing.assert_array_equal(source[1:4],[0.,0.,0.])


def test_external_work_gradient_has_correct_sign_at_two_rotation_steps():
    x=np.array([[0.,0.,0.],[4.,3.,1.]])
    moments=np.array([.1,.2,.25]);r=Rotation.from_rotvec([.2,-.1,.3]).as_matrix()
    _,body_tau,_=body_field(x,np.array([1.,.2]),r,moments,0,1.)
    tau=r@body_tau;omega=np.array([.3,.4,-.2])
    for h in (1e-4,5e-5):
        g=[]
        for axis in np.eye(3):
            e=[body_field(x,np.array([1.,.2]),Rotation.from_rotvec(sign*h*axis).as_matrix()@r,moments,0,1.)[2] for sign in (1,-1)]
            g.append((e[0]-e[1])/(2*h))
        assert np.linalg.norm(np.array(g)+tau)/np.linalg.norm(tau)<2e-6
        assert abs(np.dot(g,omega)-control.external_source(omega,tau)[0])/(np.linalg.norm(omega)*np.linalg.norm(tau))<2e-6


@pytest.mark.parametrize('bad',[[0.,0.],[0.,0.,np.nan]])
def test_invalid_external_source_is_rejected(bad):
    with pytest.raises(ValueError,match='Finite spatial'):control.external_source(bad,[1.,2.,3.])


def test_vector_identity_retains_cancellation_and_does_not_add_scalar_maxima():
    free=np.tile([3.,4.,0.],(1462,1));controlled=np.tile([-3.,4.,0.],(1462,1));expected=np.zeros_like(free)
    arrays,row=audit.vector_decomposition(free,controlled,expected,1.)
    np.testing.assert_array_equal(arrays['identity_vector'],np.zeros_like(free))
    assert row['switch_maximum_metres']==6. and row['identity_maximum_metres']==0.
    assert np.linalg.norm(arrays['free_pair_vector'][0])==5.
    assert np.linalg.norm(arrays['control_pair_vector'][0])==5.
    assert row['signed_switch_projection_at_worst_free']==pytest.approx(18/25)


@pytest.mark.parametrize('bad',['short','nan','unit'])
def test_invalid_intervention_vectors_are_rejected(bad):
    x=np.zeros((1462,3));f=x.copy();unit=1.
    if bad=='short':f=f[:-1]
    if bad=='nan':f[5,1]=np.nan
    if bad=='unit':unit=0.
    with pytest.raises(ValueError,match='Finite complete'):audit.vector_decomposition(f,x,x,unit)


def valid_evidence():
    data=dict(position_m=np.zeros((1462,10)),velocity_m_s=np.zeros((1462,10)),pair_vector_m=np.zeros((1462,3)))
    group=audit.statistics(data,np.ones(1462,dtype=bool))
    comp=dict(per_body_metres=[0.]*10,all_body_metres=0.,pair_metres=0.,velocity_m_s=0.,attitude_frobenius=0.,spin_relative_initial=0.)
    a=dict(jobs={},external={},windows={},comparisons={k:deepcopy(comp) for k in audit.annual.short.LIMITS},
        intervention=dict(identity_maximum_metres=0.,switch_maximum_metres=0.,sensitivity_scale_metres=0.,
            resolved_within_controlled_model=False,real_lunar_cause_proven=False),probes=[])
    for name in audit.JOBS:
        a['jobs'][name]=dict(samples=1462,balances=dict(checks_passed=True,closed_system=False,rotational_energy_included=False,
            source_visibility_qualified=False,source_integrals={k:{} for k in ('pn2','pn_q','external_prescription')},
            corrected=dict(energy=0.,momentum=0.,angular=0.),precision_rows=[dict(index=i,maximum_scaled=0.) for i in audit.annual.PRECISION_INDICES]))
        a['external'][name]=deepcopy(group)
        a['windows'][name]={f'{x}-{y}':dict(deepcopy(group),samples=int((y-x)*4)+1) for x,y in audit.annual.WINDOWS}
    for i in audit.annual.PRECISION_INDICES:
        a['probes'].append(dict(index=i,checks_passed=True,force_relative=0.,torque_relative=0.,potential_relative=0.,
            linear_relative=0.,angular_relative=0.,gradients=[dict(step_rad=h,torque_relative=0.,power_relative=0.) for h in (1e-4,5e-5)],
            missing_work_signal=1.,wrong_work_sign_signal=2.,missing_torque_signal=1.,wrong_torque_sign_signal=2.))
    return dict(complete=True,samples=1462,duration_seconds=31557600.,times_seconds=audit.TIMES.tolist(),
        jobs={name:dict(samples=1462) for name in audit.JOBS},analysis=a,prescribed_orientation_is_external=True,
        free_forecast=False,runtime_modified=False,parameters_fitted=False,network_used=False,real_lunar_cause_proven=False)


@pytest.mark.parametrize('bad',['energy','momentum','angular','source','precision','body','nan','identity','effect','probe','negative_control','free_claim'])
def test_true_flags_cannot_hide_failed_control_evidence(bad):
    r=valid_evidence();assert audit.qualification(r);a=r['analysis']
    if bad in ('energy','momentum','angular'):a['jobs']['tight']['balances']['corrected'][bad]=2e-11
    if bad=='source':a['jobs']['tight']['balances']['source_integrals'].pop('external_prescription')
    if bad=='precision':a['jobs']['tight']['balances']['precision_rows'][-1]['maximum_scaled']=1e-29
    if bad=='body':a['external']['tight']['bodies'].pop('Neptune')
    if bad=='nan':a['external']['tight']['pair_rms_metres']=np.nan
    if bad=='identity':a['intervention']['identity_maximum_metres']=2e-6
    if bad=='effect':a['intervention']['resolved_within_controlled_model']=True
    if bad=='probe':a['probes'][0]['gradients'][0]['power_relative']=3e-6
    if bad=='negative_control':
        for p in a['probes']:p['missing_work_signal']=0.
    if bad=='free_claim':r['free_forecast']=True
    assert not audit.qualification(r)


def test_no_residual_improvement_is_required_to_qualify_diagnostic():
    r=valid_evidence();r['analysis']['external']['tight']['pair_maximum_metres']=1e6
    assert audit.qualification(r)


def test_fresh_output_and_incomplete_ensemble_are_rejected(tmp_path,monkeypatch):
    with pytest.raises(ValueError,match='four control'):audit.load_trajectories(tmp_path,dict(jobs={}))
    monkeypatch.setattr(audit,'ROOT',tmp_path);out=tmp_path/'.tools'/'failed';out.parent.mkdir();out.with_suffix('.json').write_text('failure')
    with pytest.raises(ValueError,match='preserve failures'):audit.run(out,tmp_path/'absent',tmp_path/'absent')
    assert out.with_suffix('.json').read_text()=='failure'


def test_real_initial_adapter_removes_spin_without_changing_orbit():
    model,y,scale,_=control.initial();_,free,_=control.production.initial()
    assert y.shape==(81,) and np.all(scale>0)
    np.testing.assert_array_equal(y[:60],free[:60]);np.testing.assert_array_equal(y[60:],np.zeros(21))
    state=control.embed(y,model,*control.attitude(0.)[:2]);np.testing.assert_array_equal(state[64:67],[0.,0.,0.])
    assert len(control.rhs(0.,y,model,scale))==81
