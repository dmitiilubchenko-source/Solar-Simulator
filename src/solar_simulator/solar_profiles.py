"""Explicit access to existing Standard/Strict settings and their historical scope.

The original factory remains unchanged because scientific receipts pin its bytes.
This module selects settings; it neither changes forces nor certifies trajectories.
"""
from dataclasses import replace

from .application_profiles import solar_sandbox as standard_sandbox


PROFILES = ('standard', 'strict')
YEAR_SECONDS = 31557600


def solar_sandbox(*, profile='standard', backend='python'):
    if profile not in PROFILES:
        raise ValueError('Профиль должен быть standard или strict')
    result = standard_sandbox(backend=backend)
    if profile == 'strict':
        result = replace(result, settings=replace(result.settings, rtol=3e-14))
    return result


def profile_scope(experiment):
    """Recognize pinned inputs/settings; do not infer correctness of current states."""
    pinned = standard_sandbox(backend=experiment.settings.backend)
    vector = lambda v: (v.x, v.y, v.z)
    properties = lambda bodies: [(b.name, b.mass, b.radius, vector(b.spin)) for b in bodies]
    initial = lambda bodies: [(b.name, b.mass, b.radius, vector(b.position), vector(b.velocity), vector(b.spin)) for b in bodies]
    start_matches = (initial(experiment.initial) == initial(pinned.initial) and experiment.origin == pinned.origin
        and not experiment.initial_rotations and not experiment.rotations
        and not experiment.events and not experiment.halted
        and (experiment.time != 0 or initial(experiment.bodies) == initial(pinned.initial))
        and properties(experiment.bodies) == properties(pinned.initial))
    profile = 'custom'
    if start_matches:
        for name in PROFILES:
            if experiment.settings == solar_sandbox(profile=name, backend=experiment.settings.backend).settings:
                profile = name
                break
    within_horizon = 0 <= experiment.time <= YEAR_SECONDS
    return dict(profile=profile, pinned_start_matches=start_matches,
        historical_scope_matches=profile != 'custom' and within_horizon,
        historical_numerical_gate_passed=profile == 'strict',
        historical_packet_steps=20, historical_duration_seconds=YEAR_SECONDS,
        current_trajectory_certified=False,
        qualification_report='docs/solar-working-profile.md',
        limitations='Historical sampled checks only; batch/epoch grid matter. No guarantee for edited systems, between outputs or current runtime trajectory.')


def profile_text(experiment):
    scope = profile_scope(experiment)
    if not scope['historical_scope_matches']:
        return ''
    if scope['profile'] == 'standard':
        return 'Standard: численный критерий 0,1 м не пройден для Rust; для проверенных настроек выберите Strict.'
    return 'Strict: совпадают старт и настройки исторической проверки (год, пакет 20); не гарантия точности текущей траектории.'
