"""Opt-in explanation of existing diagnostics; no evolution or accuracy oracle.

Keep numerical diagnostics and the historical cli.report JSON unchanged. A
checkpoint describes settings/state, not its complete execution provenance.
"""
from importlib import import_module

from . import cli
from .oblateness import prescribed


def _native_status(experiment):
    if experiment.settings.backend!='rust':
        return dict(required=False,status='not_required',message='Текущие настройки используют Python; native не требуется.')
    from .recipe import _native
    function='point_acceleration' if experiment.settings.integrator=='dop853' else 'evolve'
    if experiment.settings.integrator=='verlet' and any(b.radius for b in experiment.bodies):
        function='simulate_collisions' if experiment.settings.contact_mode=='bounce' else 'run_until_contact'
    try:
        fingerprint=_native('rust')  # Existing compiled-loader/SHA check, not a force call.
        if not callable(getattr(import_module('solar_native'),function,None)):
            raise RuntimeError('Required API missing')
    except (ImportError,OSError,RuntimeError,AttributeError,TypeError):
        return dict(required=True,status='unavailable',required_api=function,
            message='Compiled solar_native отсутствует или несовместим. Диагностика состояния доступна, расчёт Rust требует исправной библиотеки.')
    return dict(required=True,status='available',required_api=function,fingerprint=fingerprint,
        message='Проверена доступность API и библиотеки для текущих настроек; это не доказательство backend прошлых вычислений.')


def _qualification(experiment):
    from .solar_profiles import profile_scope
    try:
        profile=profile_scope(experiment)
        name=profile['profile']
        # Input/settings recognition is separate from the old one-year scope.
        # Neither property qualifies the current trajectory.
        matches=name in ('standard','strict')
    except (ValueError,RuntimeError,OSError):
        name='unknown';matches=False
    return dict(status='not_established_for_current_trajectory',current_trajectory_certified=False,input_profile=name,
        current_factory_input_settings_match=matches,source_environment_and_packet_history_verified=False,
        message='Профиль сравнивается только с factory текущей установки. Это не проверка исторических SHA. История пакетов, среда и текущая траектория этой командой не аттестуются.',
        evidence=[dict(report='docs/current-runtime-375-validation.md',
            scope='375: 10 тел DE441, 1 год, EIH1PN + fixed Sun/Earth J2, Strict/per-body/relative Earth–Moon; 125 эпох и 9 holdout, конкретные пакеты и native/env.'),
            dict(report='docs/runtime-reliability-376.md',
            scope='376: 4 фиксированных Newton двухтельных IC, e=.5/.95/.99 с peri/apo, 1 период, 49 эпох; Python/Rust, два rtol и координатных представления. High-e ошибка измерена, универсального допуска нет.')])


def report(experiment):
    """Return legacy report plus versioned, explicitly requested explanation."""
    result=cli.report(experiment)
    settings=experiment.settings
    dynamic=bool(experiment.rotations)
    figures=bool(settings.figures)
    moving=prescribed(settings.figures)
    contacts=bool(experiment.events) or any(b.radius for b in experiment.initial+experiment.bodies)
    pn=settings.physics=='eih-1pn'
    if dynamic:
        model='newtonian-dynamic-q2'
        description='Ньютоновское движение с одной динамической rigid Q2-фигурой.'
        energy_basis='Орбитальная + rigid-spin энергия и потенциал одной динамической Q2-фигуры.'
        energy_status='conservative_total'
        angular_status='conservative_orbit_plus_dynamic_spin'
    elif pn:
        model='eih-1pn'
        description='Монопольная гравитация с EIH-поправками первого постньютоновского порядка.'
        energy_basis='Согласованные EIH Noether-величины до порядка 1PN, не ньютоновская энергия.'
        energy_status='approximate_1pn_budget'
        angular_status='not_conserved_with_prescribed_axes' if figures else 'approximate_1pn_noether'
    else:
        model='newtonian-contacts' if contacts else 'newtonian-points'
        description='Ньютоновская гравитация и контакты сфер.' if contacts else 'Ньютоновские точечные массы.'
        energy_basis='Ньютоновская кинетическая энергия поступательного движения и гравитационный потенциал.'
        energy_status='event_corrected_budget' if contacts else 'conservative_mechanical'
        angular_status='conservative_orbit_plus_stored_spin'
    limitations=[]
    if figures:
        model+='-prescribed-q2' if moving else '-fixed-j2'
        description+=' Добавлены фигуры с заданной меняющейся ориентацией.' if moving else ' Добавлены J2-фигуры с фиксированными осями.'
        energy_basis+=' Включён потенциал заданных фигур.'
        angular_status='not_conserved_with_prescribed_axes'
        limitations.append('Заданные оси обмениваются моментом с орбитой; их spin не интегрируется.')
    if moving:
        energy_status='approximate_1pn_orientation_work_corrected_budget' if pn else 'orientation_work_corrected_budget'
        limitations.append('Энергия без учёта работы заданной ориентации не обязана сохраняться.')
    if pn:
        limitations.append('1PN: слабое поле/малые скорости; остатки включают отброшенный порядок O(c^-4).')
        if figures:limitations.append('Смешанные figure/c² члены не реализованы; это ограничение модели, не только интегратора.')
    if dynamic:
        limitations.append('Одна динамическая Q2-фигура; без EIH, приливов и контактов. Орбитальный L отдельно не сохраняется.')
    else:
        limitations.append('Stored passive spin не означает интегрирования ориентации или rigid-spin энергии.')
        if contacts:limitations.append('Контакты/отскоки/слияния: механическая энергия может меняться; нужны dissipated_energy и model_energy_offset.')
    if not pn:limitations.append('В выбранной ньютоновской модели нет EIH-поправок и приливов; это не полная физическая модель реальных тел.')
    dop=settings.integrator=='dop853'
    norm=('RotationDOP853: orbit/quaternion/angular-momentum blocks' if dynamic else
          'PerBodyDOP853' if settings.error_control=='per-body' else 'SciPy global RMS') if dop else None
    integrator='RotationDOP853 (SciPy)' if dynamic else 'DOP853 (SciPy)' if dop else 'Velocity Verlet'
    backend_path=('Rust point forces; интегрирование SciPy, модели фигур/вращения Python' if dop and settings.backend=='rust' else
                  'Python/SciPy' if dop else 'Rust/PyO3 Verlet' if settings.backend=='rust' else 'Python Verlet')
    adaptive=None
    if dop:
        adaptive=dict(rtol=settings.rtol,position_atol_metres=settings.position_atol,
            velocity_atol_m_per_s=settings.velocity_atol,error_control=settings.error_control,
            effective_error_norm=norm,relative_pair=list(settings.relative_pair) if settings.relative_pair else None,
            interpretation='Допуски управляют локальной оценкой solver, не глобальной ошибкой орбиты.')
        if dynamic:adaptive['rotation_tolerances']=[dict(body=r.body,quaternion_atol=r.quaternion_atol,
            momentum_atol_kg_m2_s=r.momentum_atol) for r in experiment.rotations]
    detail=dict(schema=1,units=dict(mass='kg',position='m',velocity='m/s',time='s',energy='J',
        momentum='kg*m/s',angular_momentum='kg*m^2/s'),
        model=dict(id=model,description=description,physics=settings.physics,energy_basis=energy_basis,limitations=limitations,
            conservation_scope=result['conservation_scope']),
        execution=dict(integrator=integrator,configured_backend=settings.backend,implementation=backend_path,
            source='settings for ordinary advance; not attestation of previous calls',past_execution_verified=False,
            native=_native_status(experiment),adaptive_controls=adaptive),
        time_and_packets=dict(state_time_seconds=experiment.time,configured_dt_seconds=settings.dt,
            dt_role='Базовый интервал пакета: duration=dt*steps; не внутренний шаг solver.' if dop else 'Номинальный шаг Verlet; конечный шаг до заданного времени может быть короче.',
            configured_physical_step_seconds=None if dop else settings.dt,
            internal_step_seconds=None,output_cadence_seconds=None,
            last_packet_steps=None,last_packet_duration_seconds=None,packet_history_available=False,
            message='Checkpoint не хранит расписание выдачи и границы всех пакетов. Другие границы меняют численный путь.',
            recipe_command='python -m solar_simulator check-recipe <каталог_траектории>'),
        invariants=dict(energy=dict(value=result['energy_joules'],unit='J',basis=energy_basis,status=energy_status),
            momentum=dict(value=result['momentum'],unit='kg*m/s',status='approximate_1pn_noether' if pn else 'conservative_total'),
            angular_momentum=dict(value=result['angular_momentum'],unit='kg*m^2/s',status=angular_status),
            energy_budget=dict(residual_joules=result['energy_budget_residual_joules'],
                dissipated_joules=result['dissipated_energy_joules'],model_offset_joules=result['model_energy_offset_joules'],
                orientation_work_joules=result['orientation_work_joules'],
                expression='E + dissipated + model_offset - orientation_work - initial_E'),
            center_of_mass_interpretation='Ньютоновский описательный COM, не 1PN центр энергии.' if pn else 'Ньютоновский центр масс.'),
        qualification=_qualification(experiment),
        accuracy=dict(global_position_error_metres=None,global_velocity_error_m_per_s=None,jpl_residual_metres=None,
            status='not_measured_for_this_checkpoint',
            explanation='Дрейф инвариантов не равен ошибке координат/скоростей. Численная ошибка требует независимого эталона или обоснованной процедуры; JPL residual — отдельное сравнение согласованных эпох, осей, шкал времени и моделей.'))
    result['numerical_reliability']=detail
    return result
