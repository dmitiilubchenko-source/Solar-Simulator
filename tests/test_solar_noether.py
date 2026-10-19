"""Do not confuse tiny source integrals with directly resolved balance signals."""
import numpy as np
import pytest

from scripts.assess_solar_noether import (epoch_grid,packet_check,snapshot_controls,
    budget_refinement,observability,run)
from scripts.fixed_j2_year import inputs
from scripts.fixed_j2_ias import entries,scales
from scripts.assess_sandbox_planets import states


def test_ten_body_tensor_vector_runtime_gradient_and_reaction_controls():
    seed,*_ = inputs()
    row = snapshot_controls(seed)
    assert row['checks_passed']
    assert row['missing_source_scaled_net_force'] > 1e-3


def test_three_day_grid_preserves_full_twenty_hour_packets_and_final_twelve_hours():
    np.testing.assert_array_equal(epoch_grid(),[0.,72000.,144000.,216000.,259200.])
    stats = dict(packets=4,finished=True,failed=False,packet_endpoints=epoch_grid()[1:].tolist())
    packet_check(stats)
    stats['packet_endpoints'][0] = 21600.
    with pytest.raises(AssertionError):packet_check(stats)


def test_small_global_budget_difference_does_not_hide_bad_source_relative_refinement():
    old = np.zeros((5,3,7));current = old.copy()
    current[-1,1,0] = 1e-20
    row = budget_refinement(old,current,np.ones(7))
    assert row['maximum_scaled_component'] < 1e-12
    assert not row['checks_passed'] and row['groups']['pn2']['energy']['relative_difference'] == 1.
    assert row['groups']['figure_torque']['energy']['checks_passed']


def test_zero_or_disappearing_source_is_not_normalized_by_an_added_epsilon():
    old = np.zeros((5,3,7));current = old.copy()
    old[-1,1,0] = 1e-20
    row = budget_refinement(old,current,np.ones(7))
    assert not row['checks_passed']
    assert row['groups']['pn2']['energy']['relative_difference'] is None


@pytest.mark.parametrize('kind',['nan','shape','zero_scale','negative_scale'])
def test_invalid_source_integrals_and_scales_are_rejected(kind):
    old = np.zeros((5,3,7));current = old.copy();scale = np.ones(7)
    if kind == 'nan':current[1,1,1] = np.nan
    if kind == 'shape':current = current[:-1]
    if kind == 'zero_scale':scale[0] = 0.
    if kind == 'negative_scale':scale[0] = -1.
    with pytest.raises(ValueError):budget_refinement(old,current,scale)


def test_balances_below_a_loose_global_gate_do_not_qualify_unresolved_sources():
    seed,*_ = inputs()
    value = states(seed.bodies)
    values = np.tile(value,(5,1,1))
    scale = scales(value,np.array([b.mass for b in seed.bodies]),entries(seed),seed.settings.physics)
    budget = np.zeros((5,3,7));budget[-1,1,0] = 1e-20*scale[0]
    row = observability(values,budget,values,budget,seed)
    assert not row['checks_passed'] and not row['resolution_is_rigorous_bound']
    assert row['groups']['pn2']['energy']['signal_to_resolution'] < 1.
    assert row['groups']['figure_torque']['energy']['checks_passed']


def test_existing_pilot_evidence_is_preserved_before_reading_inputs(monkeypatch,tmp_path):
    from scripts import assess_solar_noether as module
    monkeypatch.setattr(module,'ROOT',tmp_path)
    output = tmp_path/'.tools'/'kept';output.parent.mkdir()
    output.with_suffix('.json').write_bytes(b'retained failure')
    with pytest.raises(ValueError,match='fresh'):run(output)
    assert output.with_suffix('.json').read_bytes() == b'retained failure'
