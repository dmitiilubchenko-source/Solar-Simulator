"""Independent research rotor limits; no yearly JPL fit or runtime activation."""
from dataclasses import replace
import numpy as np
import pytest

from scripts import free_lunar_rotation as prod
from scripts import independent_free_lunar as ref
from scripts import free_lunar_diagnostics as diag
from scripts import assess_free_lunar_rotation as audit
from scripts.canonical_initial import SIUnits
from solar_simulator.coordinates import PairCoordinates
from solar_simulator.rotation import RigidFigure, rotation_matrix
from solar_simulator.simulation import G


def model_pair():
    unit = SIUnits(1e15,12000.,G); masses = (.7*unit.mass_kg,.3*unit.mass_kg)
    figure = RigidFigure(masses[1],tuple(np.array([.001,.0012,.0014])*unit.inertia_kg_m2),.1*unit.length_m)
    quaternion = np.array([.96,.1,-.2,.15]); quaternion /= np.linalg.norm(quaternion)
    model = prod.Model(masses,figure,tuple(quaternion),(0.,0.,.003*unit.spin_kg_m2_s),
        PairCoordinates(0,1,.7,.3),(),(),unit)
    y = np.r_[np.zeros(3),[1.,0.,0.],np.zeros(3),[0.,1.,0.],model.quaternion,[0.,0.,1.],np.zeros(21)]
    return model,y


def test_free_rhs_agrees_with_independent_body_euler_and_field_reaction():
    model,y = model_pair(); scale = diag.scales(y,model)
    left = prod.rhs(0.,y,model,scale); reference = ref.initial(y,model); right = ref.rhs(0.,reference,model,scale)
    np.testing.assert_allclose(left[:12],right[:12],rtol=3e-13,atol=1e-15)
    _,_,_,q,s = prod.unpack(y,model); r = rotation_matrix(q)
    # Spatial dS = dR Pi + R dPi, including the Euler transport cancellation.
    spatial = right[12:21].reshape(3,3)@(r.T@s)+r@right[21:24]
    np.testing.assert_allclose(left[16:19],spatial,rtol=3e-13,atol=1e-15)
    assert audit.initial_bridge(model,y)['checks_passed']


def test_initial_encoded_pair_matches_physical_roundtrip():
    model,y = model_pair(); x,v,rho,_,_ = prod.unpack(y,model)
    np.testing.assert_allclose(x[1]-x[0],rho,rtol=0,atol=1e-15)
    np.testing.assert_allclose(model.pair.encode(x).ravel(),y[:6],rtol=0,atol=1e-15)
    np.testing.assert_allclose(np.sum(model.masses[:,None]*v,axis=0),0.,atol=1e-15)


def test_no_lunar_q_baseline_has_analytic_circular_kepler_limit():
    model,y = model_pair(); times = np.linspace(0.,.2*model.units.time_s,5)
    result,_ = prod.integrate(model,y,times,diag.scales(y,model),tight=True,active=False)
    expected = np.c_[np.cos(times/model.units.time_s),np.sin(times/model.units.time_s),np.zeros(5)]
    np.testing.assert_allclose(result[:,3:6],expected,rtol=0.,atol=2e-12)
    np.testing.assert_array_equal(result[:,16:19],np.tile(y[16:19],(5,1)))


def test_rhs_never_reads_future_attitude(monkeypatch):
    from solar_simulator import orientation,spin_initial
    def forbidden(*a,**k):raise AssertionError('Future attitude is forbidden in RHS')
    monkeypatch.setattr(orientation,'lunar_rotation',forbidden)
    monkeypatch.setattr(spin_initial,'lunar_solid_equivalent_initial',forbidden)
    model,y = model_pair(); scale = diag.scales(y,model)
    assert np.isfinite(prod.rhs(1.,y,model,scale)).all()
    assert np.isfinite(ref.rhs(1.,ref.initial(y,model),model,scale)).all()


def test_decimal_readout_agrees_across_precision_and_rotor_representations():
    model,y = model_pair(); matrix_y = ref.initial(y,model)
    a = diag.readout(y,model,precision=70); b = diag.readout(y,model,precision=90)
    assert max(abs(x-z) for x,z in zip(a,b)) < 1e-60
    c = diag.readout(matrix_y,model,reference=True)
    np.testing.assert_allclose(list(map(float,a)),list(map(float,c)),rtol=2e-14,atol=1e-18)
    with pytest.raises(ValueError):diag.readout(y,model,precision=28)


@pytest.mark.parametrize('bad',['nan','coincident','strong','inside'])
def test_both_rhs_reject_unsupported_geometry(bad):
    model,y = model_pair(); scale = diag.scales(y,model)
    if bad == 'nan':y[0] = np.nan
    if bad == 'coincident':y[3:6] = 0.
    if bad == 'strong':y[9] = model.c
    if bad == 'inside':y[3:6] = [.01,0.,0.]
    with pytest.raises(ValueError):prod.rhs(0.,y,model,scale)
    if bad != 'nan':
        with pytest.raises(ValueError):ref.rhs(0.,ref.initial(y,model),model,scale)


def test_pair_only_error_is_visible_in_comparison_and_bad_metrics_fail():
    model,y = model_pair(); values = np.tile(y,(3,1)); changed = values.copy(); changed[:,3] += 1e-8
    row = diag.comparison(values,changed,model)
    assert row['pair_metres'] == pytest.approx(1e-8*model.units.length_m,rel=1e-7)
    row['pair_metres'] = float('nan')
    assert not diag.within(row,(4.,.2,1e-5,2e-7,2e-7))
    assert not audit.qualification(dict(complete=True,samples=129,jobs={},comparisons={}))


def test_fresh_output_guard_preserves_failed_receipt(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'ROOT',tmp_path)
    output = tmp_path/'.tools'/'failed'; output.parent.mkdir(); output.with_suffix('.json').write_text('failed')
    with pytest.raises(ValueError,match='preserve failures'):audit.run(output,tmp_path/'missing.json')
    assert output.with_suffix('.json').read_text() == 'failed'


def test_model_rejects_wrong_pair_mass_fraction():
    model,_ = model_pair()
    with pytest.raises(ValueError):replace(model,pair=PairCoordinates(0,1,.5,.5))


def test_true_flags_cannot_qualify_missing_body_or_balance_evidence():
    report = dict(complete=True,samples=129,duration_seconds=32*86400.,initial_bridge=dict(checks_passed=True),
        comparisons={name:dict(all_body_metres=0.,pair_metres=0.,velocity_m_s=0.,attitude_frobenius=0.,
            spin_relative_initial=0.,per_body_metres=[0.]*10) for name in audit.LIMITS},
        jobs={name:dict(samples=129,raw_rotation_defect=0.,balances=dict(checks_passed=True)) for name in audit.JOBS})
    assert not audit.qualification(report)
    report['comparisons']['independent']['per_body_metres'] = [0.]*9
    assert not audit.qualification(report)
