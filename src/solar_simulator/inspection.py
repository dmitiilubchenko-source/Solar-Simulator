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


def _execution(experiment,*,include_native=True):
    """Explain settings without computing forces, invariants or a trajectory."""
    settings=experiment.settings
    dynamic=bool(experiment.rotations)
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
    result=dict(integrator=integrator,configured_backend=settings.backend,implementation=backend_path,
        source='settings for ordinary advance; not attestation of previous calls',past_execution_verified=False)
    if include_native:result['native']=_native_status(experiment)
    result['adaptive_controls']=adaptive
    return result


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
    detail=dict(schema=1,units=dict(mass='kg',position='m',velocity='m/s',time='s',energy='J',
        momentum='kg*m/s',angular_momentum='kg*m^2/s'),
        model=dict(id=model,description=description,physics=settings.physics,energy_basis=energy_basis,limitations=limitations,
            conservation_scope=result['conservation_scope']),
        execution=_execution(experiment),
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


def recipe_report(trajectory):
    """Explain a verified recording; never attach history to a loose checkpoint.

    Trajectory owns the verified frame-byte snapshot. read_recipe/audit_recipe
    retain their existing strict checks; environment mismatch is not corruption.
    """
    from .recipe import audit_recipe,read_recipe
    payload=read_recipe(trajectory)
    unavailable=None
    try:result=audit_recipe(trajectory)
    except (ImportError,RuntimeError) as error:
        # read_recipe has already verified stored evidence. Its validation
        # errors (ValueError/OSError) are NOT downgraded to environment failures.
        unavailable=type(error).__name__
        result=dict(compatible=False,differences=['current-environment-unavailable'],
            samples=len(trajectory.times),stable=payload['stable'],
            unverified_dependencies=None,physical_accuracy_claim=False)
    first,_=trajectory.frame(0)
    metadata=trajectory.metadata
    comparison_differences=None if unavailable else [key for key in result['differences']
        if key not in ('recording-environment-changed','dependency-inventory-unverified')]
    result['recording_reliability']=dict(schema=1,units='SI',
        manifest_status=metadata['status'],confirmed_frame_count=len(trajectory.times),
        completed_packet_count=len(payload['packet_boundaries_seconds']),
        packet_boundaries_seconds=payload['packet_boundaries_seconds'],
        configured_packet_steps=metadata['packet_steps'],
        start_time_seconds=trajectory.times[0],last_confirmed_time_seconds=trajectory.times[-1],
        requested_target_seconds=metadata['requested_target_seconds'],
        requested_target_reached=trajectory.times[-1]==metadata['requested_target_seconds'],
        time_basis='Секунды от начала опыта, не Unix time. Пакеты — опубликованные пары кадров, включая возможный контакт на той же эпохе.',
        initial_frame=dict(file=metadata['frames'][0]['file'],sha256=metadata['frames'][0]['sha256'],
            configured_dt_seconds=first.settings.dt,physics=first.settings.physics,
            execution=_execution(first,include_native=False)),
        integrity=dict(status='verified_against_stored_hashes',recipe_schema_version=payload['schema_version'],
            manifest_sha256=payload['manifest_sha256'],verified_frames=metadata['frames'],
            scope='Проверены recipe envelope SHA, связь с manifest и SHA/схемы всех загруженных кадров. Это snapshot, не подпись автора и не аттестация исполнения.'),
        recording_environment=dict(endpoint_fingerprints_equal=payload['stable'],continuous_monitoring_verified=False,
            scope='Сравнены fingerprints начала и конца записи; изменения с возвратом между ними не исключаются.'),
        current_environment=dict(status='unavailable' if unavailable else 'compared',failure_type=unavailable,
            recorded_start_fields_match=None if unavailable else not comparison_differences,
            fingerprint_differences=comparison_differences,unverified_dependencies=result['unverified_dependencies'],
            scope='Сравнение с fingerprint_start записи. Изменение кода/среды означает несовместимость строгого replay, а не повреждение кадров.'),
        reproducibility=dict(strict_replay_preconditions_met=result['compatible'],replay_performed=False,
            reproduced_prefix=None,message='Проверка условий не заменяет фактическое воспроизведение. Орбиты не интегрировались.'),
        accuracy=dict(physical_accuracy_claim=False,numerical_accuracy_assessed=False,
            message='Целостность, совпадение fingerprints и даже успешный replay не доказывают физическую/численную точность.'),
        unrecorded=dict(internal_steps_seconds=None,rejected_attempts=None,controller_state=None))
    return result
