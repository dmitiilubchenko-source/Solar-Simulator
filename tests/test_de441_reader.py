"""Known synthetic polynomials and corruption controls, never fitted orbit tests."""
from math import cos, sin, pi

import numpy as np
import pytest

from scripts import de441_reader as module


@pytest.mark.parametrize('x', [-1., .25, 1.])
def test_cubic_value_and_two_derivatives_have_known_seconds_scaling(x):
    c = np.array([[1., 2., 3., 4.]])
    expected = [1+2*x+3*(2*x*x-1)+4*(4*x**3-3*x),
        (2+12*x+4*(12*x*x-3))/200., (12+96*x)/200.**2]
    for order, value in enumerate(expected):
        np.testing.assert_allclose(module.polynomial(c, x, 400., order), [value], rtol=1e-14, atol=1e-14)


def synthetic():
    layout = np.zeros((3, 15), dtype=int)
    values = np.zeros(1018)
    values[:2] = [module.EPOCH, module.EPOCH+32.]
    offset = 3
    for slot in range(11):
        parts = 2 if slot == 0 else 1
        layout[:, slot] = [offset, 4, parts]
        for segment in range(parts):
            first = offset-1+segment*12
            values[first:first+12] = np.column_stack((np.array([100., 200., 300.])*slot,
                np.zeros((3, 3)))).ravel()
        offset += 12*parts
    # Unambiguous different constants exercise selection, not continuity.
    values[2] = 1.
    values[14] = 10.
    header = ('GROUP   1040\n2 DENUM EMRAT\nGROUP   1041\n2 441 2\nGROUP   1050\n'+
        '\n'.join(' '.join(map(str, row)) for row in layout)+'\nGROUP   1070\n').encode()
    raw = ('306 1018\n'+' '.join(map(str, values))).encode()
    return header, raw


def test_subintervals_and_terminal_endpoint_are_selected_without_clipping():
    reader = module.Reader(*synthetic())
    assert reader.component(0, 0.)[0] == 1.
    assert reader.component(0, 16*module.DAY-1.)[0] == 1.
    assert reader.component(0, 16*module.DAY)[0] == 10.
    assert reader.component(0, 32*module.DAY)[0] == 10.
    with pytest.raises(ValueError):
        reader.component(0, np.nextafter(32*module.DAY, np.inf))


def test_earth_and_moon_use_emb_mass_ratio_and_fixed_inertial_rotation_in_si():
    reader = module.Reader(*synthetic())
    q = reader.vectors(0.)
    angle = 84381.448*pi/(180*3600)
    def rotate(v):
        x, y, z = v
        return np.array([x, cos(angle)*y+sin(angle)*z, -sin(angle)*y+cos(angle)*z])*1000.
    np.testing.assert_allclose(q[3], rotate([-100., -200., -300.]), rtol=1e-15, atol=1e-9)
    np.testing.assert_allclose(q[4], rotate([800., 1600., 2400.]), rtol=1e-15, atol=1e-9)
    np.testing.assert_allclose(reader.relative(0.), rotate([900., 1800., 2700.]), rtol=1e-15, atol=1e-9)
    np.testing.assert_allclose((2*q[3]+q[4])/3, rotate([200., 400., 600.]), rtol=1e-15, atol=1e-9)
    np.testing.assert_array_equal(reader.states(0.)[:, 3:], 0.)


@pytest.mark.parametrize('seconds', [-1., float('nan'), float('inf'), True, '1', 315576001.])
def test_unsupported_time_is_rejected(seconds):
    with pytest.raises(ValueError):
        module.Reader(*synthetic()).states(seconds)


@pytest.mark.parametrize('change', ['truncated', 'count', 'nan', 'pointer', 'overlap', 'missing_slot'])
def test_corrupt_records_or_layout_are_rejected(change):
    header, raw = synthetic()
    if change == 'truncated': raw = raw[:-10]
    elif change == 'count': raw = raw.replace(b'306 1018', b'306 1017')
    elif change == 'nan': raw = raw.replace(b'1.0 ', b'nan ', 1)
    elif change == 'pointer': header = header.replace(b'3 27 ', b'1010 27 ', 1)
    elif change == 'overlap': header = header.replace(b'3 27 ', b'3 3 ', 1)
    else: header = header.replace(b'4 4 4', b'0 4 4', 1)
    with pytest.raises(ValueError):
        module.Reader(header, raw)


def test_nutation_or_libration_columns_are_not_silently_treated_as_positions():
    reader = module.Reader(*synthetic())
    for slot in (-1, 11, 12, True):
        with pytest.raises(ValueError): reader.component(slot, 0.)
        with pytest.raises(ValueError): reader.coefficients(0, slot, 0)


def test_archived_inputs_reject_any_byte_change(tmp_path):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    bad = tmp_path/'changed.zip'
    bad.write_bytes((root/module.ARCHIVE).read_bytes()+b'X')
    with pytest.raises(ValueError, match='archive SHA'):
        module.load_archive(bad)
