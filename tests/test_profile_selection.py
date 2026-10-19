"""Profile selection must reproduce pinned inputs, not confer universal accuracy."""
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys

import pytest

from solar_simulator.storage import load, to_document


@pytest.mark.parametrize('backend', ['python', 'rust'])
def test_strict_selection_exactly_matches_saved_checkpoint(backend):
    from solar_simulator.solar_profiles import solar_sandbox, profile_scope
    pinned = load('docs/solar-sandbox-strict-checkpoint.json')
    expected = replace(pinned, settings=replace(pinned.settings, backend=backend))
    actual = solar_sandbox(profile='strict', backend=backend)
    assert to_document(actual) == to_document(expected)
    scope = profile_scope(actual)
    assert scope['profile'] == 'strict' and scope['pinned_start_matches']
    assert not scope['current_trajectory_certified'] and scope['historical_packet_steps'] == 20


def test_standard_default_preserves_existing_factory_and_failure_scope():
    from solar_simulator.application_profiles import solar_sandbox as original
    from solar_simulator.solar_profiles import solar_sandbox, profile_scope
    assert to_document(solar_sandbox()) == to_document(original())
    scope = profile_scope(solar_sandbox())
    assert scope['profile'] == 'standard' and not scope['historical_numerical_gate_passed']
    with pytest.raises(ValueError): solar_sandbox(profile='STRICT-ish')


@pytest.mark.parametrize('change', ['rtol', 'dt', 'bodies', 'current', 'origin', 'horizon'])
def test_profile_label_does_not_qualify_edited_or_out_of_scope_states(change):
    from solar_simulator.solar_profiles import solar_sandbox, profile_scope
    original = solar_sandbox(profile='strict')
    if change == 'rtol': altered = replace(original, settings=replace(original.settings, rtol=1e-12))
    elif change == 'dt': altered = replace(original, settings=replace(original.settings, dt=7200))
    elif change == 'bodies': altered = replace(original, initial=original.initial[:-1])
    elif change == 'current': altered = replace(original, bodies=original.bodies[:-1])
    elif change == 'origin': altered = replace(original, origin=None)
    else: altered = replace(original, time=31557600.25)
    scope = profile_scope(altered)
    assert not scope['historical_scope_matches'] and not scope['current_trajectory_certified']


@pytest.mark.parametrize('profile', ['standard', 'strict'])
def test_cli_explicit_profile_roundtrip_and_report(tmp_path, profile):
    from solar_simulator.solar_profiles import solar_sandbox
    path = tmp_path/'selected profile.json'
    result = subprocess.run([sys.executable, '-X', 'utf8', '-B', '-m', 'solar_simulator',
        'solar-sandbox', str(path), '--profile', profile], capture_output=True, text=True, encoding='utf-8')
    assert result.returncode == 0, result.stderr
    assert to_document(load(path)) == to_document(solar_sandbox(profile=profile))
    assert json.loads(result.stdout)['solar_profile']['profile'] == profile


@pytest.mark.parametrize('backend', ['python', 'rust'])
def test_selected_strict_continuation_matches_original_pinned_path(backend):
    from solar_simulator.solar_profiles import solar_sandbox
    from solar_simulator.time_control import advance_towards
    pinned = load('docs/solar-sandbox-strict-checkpoint.json')
    pinned = replace(pinned, settings=replace(pinned.settings, backend=backend))
    selected = solar_sandbox(profile='strict', backend=backend)
    for target in (10000.25, 20000.5):
        pinned = advance_towards(pinned, target)
        selected = advance_towards(selected, target)
        assert to_document(selected) == to_document(pinned)


def _check_gui_profiles(tmp_path):
    import tkinter as tk
    from solar_simulator.app import Laboratory
    from solar_simulator.solar_profiles import solar_sandbox
    from unittest.mock import patch
    root = tk.Tk(); root.withdraw(); app = Laboratory(root)
    try:
        before = app.experiment
        app.solar_profile.set('strict')
        assert app.experiment is before
        app._open_solar_sandbox()
        assert to_document(app.experiment) == to_document(solar_sandbox(profile='strict'))
        assert 'Strict' in app.model_info.get()
        path = tmp_path/'strict GUI.json'
        with patch('solar_simulator.app.filedialog.asksaveasfilename', return_value=str(path)): app._save()
        assert to_document(load(path)) == to_document(app.experiment)
        app.solar_profile.set('standard'); app._open_solar_sandbox()
        assert app.experiment.settings.rtol == 1e-13 and 'Standard' in app.model_info.get()
        app.rtol.set('1e-12'); app._settings()
        assert 'Strict' not in app.model_info.get() and 'Standard' not in app.model_info.get()
    finally: app.close()


def test_real_gui_profile_selection_save_and_manual_settings(tmp_path):
    from test_app_workflows import run_gui_check
    run_gui_check('_check_gui_profiles', tmp_path, source=__file__)
