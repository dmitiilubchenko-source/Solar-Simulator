"""Per-source normalization prevents a Newtonian scale from hiding a defect."""
import numpy as np
import pytest

from scripts.bridge_noether_sources import source_metrics,bridge,run
from scripts.fixed_j2_year import inputs
from scripts.fixed_j2_ias import entries
from scripts.assess_sandbox_planets import states
from solar_simulator.oblateness import prepare


def test_tiny_source_cannot_pass_because_absolute_error_is_small():
    expected=np.zeros((3,7));expected[1,0]=1e-30
    actual=expected.copy();actual[1,0]=0.
    assert not source_metrics(actual,expected)['checks_passed']


def test_spurious_exact_zero_source_is_rejected_without_epsilon():
    expected=np.zeros((3,7));actual=expected.copy();actual[0,0]=1e-100
    row=source_metrics(actual,expected)
    assert not row['checks_passed'] and row['groups']['figure_torque']['energy']['relative_error'] is None
    assert source_metrics(expected,expected)['checks_passed']


def test_real_ten_body_native_and_source_bridge():
    seed,*_=inputs()
    row=bridge(states(seed.bodies),[b.mass for b in seed.bodies],entries(seed),prepare(seed.bodies,seed.settings.figures))
    assert row['checks_passed']


@pytest.mark.parametrize('kind',['nan','shape'])
def test_invalid_source_arrays_are_rejected(kind):
    a=np.zeros((3,7));b=a.copy()
    if kind=='nan':a[1,0]=np.nan
    else:a=a[:-1]
    with pytest.raises(ValueError):source_metrics(a,b)


def test_existing_source_bridge_evidence_is_preserved(monkeypatch,tmp_path):
    from scripts import bridge_noether_sources as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    output=tmp_path/'.tools'/'kept';output.parent.mkdir()
    output.with_suffix('.json').write_bytes(b'old audit')
    with pytest.raises(ValueError,match='fresh'):run(output,'unused','unused')
    assert output.with_suffix('.json').read_bytes()==b'old audit'
