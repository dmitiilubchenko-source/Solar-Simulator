"""Analytic inversion and oracle sensitivity; never fit thresholds to JPL."""
from decimal import Decimal, localcontext
import json
from zipfile import ZipFile

import numpy as np
import pytest

from scripts import assess_lunar_inertia_field as audit
from solar_simulator.rotation import RigidFigure, pair_field


def source_arithmetic():
    with ZipFile(audit.ROOT/audit.de.ARCHIVE) as archive:
        header = audit.decimal_header(archive.read('de441-header.txt'))
    return header, json.loads((audit.ROOT/audit.SOLID).read_bytes()), json.loads((audit.ROOT/audit.ORIENTATION).read_bytes())


def test_known_integer_quadrupole_and_mean_are_inverted_independently():
    # a=2,b=3,c=4 -> J2=3/2,C22=1/4,mean=3.
    assert audit.coefficients((2,3,4)) == (1.5,.25)
    assert audit.complete_moments(3.,1.5,.25) == (2.,3.,4.)
    assert audit.coefficients((12,13,14)) == (1.5,.25)


def test_isotropic_inertia_freedom_preserves_potential_force_torque_but_not_spin():
    a = RigidFigure(10.,(20.,25.,30.),3.)
    b = RigidFigure(10.,(24.,29.,34.),3.)
    q = [1.,0.,0.,0.]
    for actual, expected in zip(pair_field(a,2.,[10.,12.,-5.],q),pair_field(b,2.,[10.,12.,-5.],q)):
        np.testing.assert_array_equal(actual, expected)
    omega = np.array([.1,.2,.3])
    assert .5*np.dot(a.moments,omega**2) != .5*np.dot(b.moments,omega**2)


def test_decimal_rounding_corners_have_analytic_widths_and_common_mean_cancels():
    result = audit.arithmetic(*source_arithmetic())
    d = Decimal
    widths = [d(b)-d(a) for a,b in result['rounding']['bounds']]
    assert widths == [d('2e-8'),d('5e-9')]
    with localcontext() as ctx:
        ctx.prec = 70
        moments = tuple(d(v) for v in result['completions'][0]['normalized_moments'])
        for shift in (d('0'),d('.000012'),-d('.000012')):
            np.testing.assert_allclose(list(map(float,audit.coefficients(tuple(v+shift for v in moments)))),
                list(map(float,audit.coefficients(moments))),rtol=1e-60,atol=0.)
    assert all(max(v['float_relative']) < 5e-12 for v in result['completions'])


def test_common_scaling_cannot_change_c22_to_j2_ratio():
    j,c = audit.coefficients((2.,3.,4.))
    for scale in (.5,2.,1024.):
        sj,sc = audit.coefficients(tuple(scale*v for v in (2.,3.,4.)))
        assert sc/sj == c/j


def test_park_inversion_satisfies_definitions_without_certifying_physics():
    result = audit.arithmetic(*source_arithmetic())
    park = result['conditional_park']
    assert abs(Decimal(park['j2_roundtrip'])) < Decimal('1e-65')
    assert abs(Decimal(park['beta_roundtrip'])) < Decimal('1e-65')
    assert abs(Decimal(park['gamma_roundtrip'])) < Decimal('1e-65')
    assert result['physical_spin_mapping_certified'] is False


@pytest.mark.parametrize('key', ['j2','c22','radius_metres'])
def test_orientation_mismatch_cannot_silently_replace_header(key):
    h,s,o = source_arithmetic()
    o['figures']['Moon'][key] *= 1.0001
    with pytest.raises(ValueError,match='exactly match'):
        audit.arithmetic(h,s,o)


def test_own_body_norm_detects_small_outer_field_hidden_by_global_max():
    expected = np.array([[1.,0.,0.],[1e-25,0.,0.]])
    actual = expected.copy(); actual[1] *= 2
    np.testing.assert_array_equal(audit.own_relative(actual,expected),[0.,1.])
    assert np.linalg.norm(actual-expected,axis=1).max()/np.linalg.norm(expected,axis=1).max() < 5e-10
    np.testing.assert_array_equal(audit.own_relative(np.zeros((2,3)),np.zeros((2,3))),[0.,0.])


@pytest.mark.parametrize('kind', ['nonfinite','shape','zero'])
def test_invalid_force_comparison_is_rejected(kind):
    expected = np.ones((2,3)); actual = expected.copy()
    if kind == 'nonfinite': actual[0,0] = np.nan
    if kind == 'shape': actual = actual[:1]
    if kind == 'zero': expected[:] = 0
    with pytest.raises(ValueError):audit.own_relative(actual,expected)


def test_grouped_metrics_retain_seam_outlier_in_overall_error():
    defect = np.zeros((3,10,3)); relative = np.zeros((3,3))
    defect[1,:,0] = 100.; relative[1,0] = 100.
    r = audit.grouped_metrics(defect,relative,np.array([0.,1.,2.]),np.array([False,True,False]))
    assert r['all']['moon_relative']['maximum_m_per_s2'] == 100
    assert r['boundary']['moon_relative']['maximum_m_per_s2'] == 100
    assert r['interior']['moon_relative']['maximum_m_per_s2'] == 0
    assert r['all']['moon_relative']['rms_m_per_s2'] == pytest.approx(100/np.sqrt(3))


def test_real_boundary_distance_is_zero_at_known_moon_segment_join():
    reader,_ = audit.de.load_archive(audit.ROOT/audit.de.ARCHIVE)
    # Reader epoch is seven days before the next 32-day record endpoint;
    # Moon has four-day segments: first following join occurs after three days.
    distances = [(t,audit.boundary_distance(reader,t*audit.de.DAY)) for t in (0.,1.,3.,7.)]
    assert distances[0][1] > 1
    assert distances[2][1] == 0
    assert distances[3][1] == 0


def test_existing_output_is_rejected_before_source_or_scientific_work(tmp_path,monkeypatch):
    monkeypatch.setattr(audit,'ROOT',tmp_path)
    path = tmp_path/'.tools/audit.json';path.parent.mkdir();path.write_text('{}')
    with pytest.raises(ValueError,match='fresh'):
        audit.run(path,tmp_path/'missing-reader.json')
