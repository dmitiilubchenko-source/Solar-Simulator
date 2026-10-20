"""Independent geometry/bound checks, without changing a physical trajectory."""
from decimal import Decimal as D, localcontext
import hashlib
import json

import numpy as np
import pytest

from scripts import diagnose_rust_adaptive as diagnosis
from scripts.diagnose_rust_adaptive import analyse_sample, alternative_bound, position_projection, run


def test_projection_has_known_three_dimensional_geometry():
    # v=(3,4,0), delta=2v+(-4,3,12): along=10, normal=13, total=sqrt269.
    reference = ((D(1),D(2),D(3)), (D(3),D(4),D(0)))
    actual = tuple(map(D,(3,13,15,3,4,0)))
    result = position_projection(actual,reference)
    assert result['time_shift_seconds'] == 2
    assert result['along_velocity_metres'] == 10
    assert result['normal_metres'] == 13
    assert result['position_metres'] == pytest.approx(269**.5)
    assert result['along_fraction'] == pytest.approx(10/269**.5)
    # Exact proper rotation by signed permutation preserves geometric norms.
    transform = lambda group: (group[1],-group[2],-group[0])
    rotated = transform(actual[:3])+transform(actual[3:])
    assert position_projection(rotated,tuple(map(transform,reference))) == result


def test_projection_sign_zero_and_orthogonal_cases():
    reference=((D(0),)*3,(D(3),D(4),D(0)))
    for delta, shift, normal in (((-6,-8,0),-2,0),((-4,3,0),0,5),((0,0,0),0,0)):
        result=position_projection(tuple(map(D,(*delta,3,4,0))),reference)
        assert result['time_shift_seconds']==shift
        assert result['normal_metres']==normal
    assert result['along_fraction'] is None


def test_exact_float_difference_does_not_depend_on_ambient_decimal_precision():
    state=[[.1,.2,.3,0.,0.,0.],[.3,.4,.5,1.,0.,0.]]
    with localcontext() as context:
        context.prec=110
        r=tuple(D.from_float(b)-D.from_float(a) for a,b in zip(state[0][:3],state[1][:3]))
    reference=(r,(D(1),D(0),D(0)))
    for precision in (9,28,110):
        with localcontext() as context:
            context.prec=precision
            error,projection=analyse_sample(state,reference)
        assert error==dict(position_metres=0.,velocity_m_per_s=0.)
        assert projection['position_metres']==0.
        assert projection['along_fraction'] is None


@pytest.mark.parametrize('velocity',[(D(0),)*3,(D('NaN'),D(0),D(1))])
def test_projection_rejects_undefined_inputs(velocity):
    with pytest.raises(ValueError):
        position_projection((D(0),)*6,((D(0),)*3,velocity))


def test_reverse_triangle_is_a_lower_bound_and_never_a_new_gate():
    error=dict(position_metres=5.,velocity_m_per_s=2e-5)
    budget=dict(position_metres=.25,velocity_m_per_s=1e-7)
    result=alternative_bound(error,budget)
    assert result['remaining_error_lower_bound']['position_metres']<=4.75
    assert result['remaining_error_lower_bound']['position_metres']==pytest.approx(4.75)
    assert result['insufficient_alone']
    # Alternative larger than observed error is inconclusive, not proof of a cause.
    result=alternative_bound(error,dict(position_metres=8.,velocity_m_per_s=3e-5))
    assert result['remaining_error_lower_bound']==dict(position_metres=0.,velocity_m_per_s=0.)
    assert not result['insufficient_alone']
    with pytest.raises(ValueError):
        alternative_bound(error,dict(position_metres=-1.,velocity_m_per_s=0.))


def test_previous_diagnosis_is_not_overwritten(tmp_path):
    output=tmp_path/'kept.json'
    output.write_bytes(b'previous diagnosis')
    with pytest.raises(FileExistsError):
        run(output)
    assert output.read_bytes()==b'previous diagnosis'


@pytest.mark.parametrize('damage',['source','archive','incomplete'])
def test_changed_or_incomplete_evidence_is_rejected(tmp_path,monkeypatch,damage):
    source=tmp_path/'solver.rs'
    source.write_bytes(b'original numerical source\n')
    archive=tmp_path/'samples.npz'
    np.savez_compressed(archive,kept=np.array([1.,2.,3.]))
    sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
    report=dict(complete=True,source_unchanged=True,checks_passed=False,
        production_eligible=False,source_sha256={'solver.rs':sha(source)},
        sample_archive='samples.npz',npz_sha256=sha(archive))
    path=tmp_path/'receipt.json'
    path.write_text(json.dumps(report))
    monkeypatch.setattr(diagnosis,'ROOT',tmp_path)
    _, arrays, _=diagnosis.load_evidence(path)
    np.testing.assert_array_equal(arrays['kept'],[1.,2.,3.])
    if damage=='source':
        source.write_bytes(b'changed numerical source\n')
    elif damage=='archive':
        # NPZ readers tolerate trailing bytes; the scientific SHA must reject it.
        archive.write_bytes(archive.read_bytes()+b'changed')
    else:
        report['complete']=False
        path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        diagnosis.load_evidence(path)
