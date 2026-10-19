"""Командная строка лаборатории: создание, продолжение, отчёт и интерфейс."""
import argparse
from dataclasses import replace, asdict
import json

from .diagnostics import model_invariants
from .experiment import PRESETS, Settings, advance, preset
from .simulation import center_of_mass
from .storage import save
from .branch_io import open_experiment, save_experiment


def report(experiment):
    physics = experiment.settings.physics
    figures = experiment.settings.figures
    initial, _, _ = model_invariants(experiment.initial, physics, figures)
    energy, momentum, angular = model_invariants(experiment.bodies, physics, figures, experiment.time)
    if experiment.rotations or experiment.initial_rotations:
        from .nbody_rotation import invariants, validate_experiment
        validate_experiment(experiment)
        initial, _, _ = invariants(experiment.initial, experiment.initial_rotations)
        energy, momentum, angular = invariants(experiment.bodies, experiment.rotations)
    def vector(value):
        return [value.x,value.y,value.z]
    scope = ("EIH Noether quantities through 1PN; residual includes omitted O(c^-4) terms; COM is Newtonian descriptive"
             if physics=="eih-1pn" else "Newtonian energy, momentum and angular momentum")
    if figures:
        if physics == "newtonian":
            scope = "Newtonian energy and linear momentum; angular momentum reported descriptively"
        scope += "; conservative fixed-axis J2 potential included; orbital angular momentum exchanges torque with fixed axes; no spin evolution"
        if physics == "eih-1pn":
            scope += "; mixed J2/c^2 terms omitted, so energy/momentum residual includes this model truncation"
    from .oblateness import orbital_torque, prescribed, prepare, orientation_power
    if prescribed(figures):
        scope = scope.replace("conservative fixed-axis J2 potential included", "prescribed time-dependent J2/C22 potential included")
        scope = scope.replace("fixed axes", "prescribed axes")
        scope += "; energy budget subtracts integral of explicit orientation power; orientation is not integrated self-consistently"
    if experiment.rotations:
        scope = "Newtonian orbital+rigid-spin energy, linear momentum and total angular momentum; one dynamic Q2 figure; no tides/EIH"
    power = 0.
    if prescribed(figures):
        import numpy as np
        p = np.array([[b.position.x,b.position.y,b.position.z] for b in experiment.bodies])
        power = orientation_power(p, np.array([b.mass for b in experiment.bodies]), prepare(experiment.bodies, figures), experiment.time)
    figure_torque = orbital_torque(experiment.bodies, figures, experiment.time) if figures else None
    spin_torque = None
    if experiment.rotations:
        import numpy as np
        from .nbody_rotation import correction, validate
        from .vector3 import Vector3
        index = validate(experiment.bodies, experiment.rotations)
        rotation = experiment.rotations[0]
        p = np.array([[b.position.x,b.position.y,b.position.z] for b in experiment.bodies])
        _, torque, _ = correction(p, np.array([b.mass for b in experiment.bodies]), index,
            rotation.figure, rotation.quaternion)
        spin_torque = Vector3(*map(float,torque))
        figure_torque = spin_torque.multiply(-1)
    return dict(origin=asdict(experiment.origin) if experiment.origin else None,
        epoch_jd_tdb=experiment.origin.epoch_jd_tdb+experiment.time/86400 if experiment.origin else None,
        physics=physics,integrator=experiment.settings.integrator,backend=experiment.settings.backend,
        error_control=experiment.settings.error_control,
        time_seconds=experiment.time,bodies=len(experiment.bodies),
        relative_pair=list(experiment.settings.relative_pair) if experiment.settings.relative_pair else None,
        conservation_scope=scope, figures=[asdict(f) for f in figures],
        rotations=[asdict(r) for r in experiment.rotations],
        orbital_angular_momentum_conserved=not bool(figures or experiment.rotations),
        figure_orbital_torque=vector(figure_torque) if figure_torque is not None else [0.0,0.0,0.0],
        dynamic_spin_torque=vector(spin_torque) if spin_torque is not None else None,
        events=len(experiment.events),halted=experiment.halted,energy_joules=energy,
        dissipated_energy_joules=experiment.dissipated_energy,
        model_energy_offset_joules=experiment.model_energy_offset,
        orientation_work_joules=experiment.orientation_work, orientation_power_watts=power,
        energy_budget_residual_joules=energy+experiment.dissipated_energy+experiment.model_energy_offset-experiment.orientation_work-initial,
        momentum=vector(momentum),
        angular_momentum=vector(angular),
        center_of_mass=vector(center_of_mass(experiment.bodies)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Solar Simulator — гравитационная лаборатория (SI)")
    commands = parser.add_subparsers(dest="command",required=True)
    new = commands.add_parser("new",help="Создать сценарий JSON")
    new.add_argument("preset",choices=PRESETS)
    new.add_argument("output")
    new.add_argument("--backend",choices=["python","rust"],default="python")
    new.add_argument("--dt",type=float)
    new.add_argument("--integrator", choices=["verlet", "dop853"], help="DOP853 для 1PN, фигур, относительной пары или точечных тел/Python; иначе Verlet")
    new.add_argument("--physics", choices=["newtonian", "eih-1pn"], default="newtonian", help="1PN требует DOP853, точечных тел и слабого поля")
    new.add_argument("--figures", choices=["none", "earth-j2", "earth-q2", "earth-moon-q2", "solar-j2", "sun-earth-moon-q2"], default="none", help="solar-j2: фиксированная солнечная J2; sun-earth-moon-q2: Солнце + заданная Earth/Moon J2/C22, до 365.25 суток от 2026-10-08 TDB")
    new.add_argument("--rtol", type=float, default=1e-13)
    new.add_argument("--position-atol", type=float, default=1e-3, help="Абсолютный допуск координат, м")
    new.add_argument("--velocity-atol", type=float, default=1e-9, help="Абсолютный допуск скорости, м/с")
    new.add_argument("--error-control", choices=["per-body", "global-rms"], default="per-body",
                     help="DOP853: отдельная ошибка каждого тела/пары или прежнее усреднение по системе")
    new.add_argument("--relative-pair", nargs=2, metavar=("FIRST","SECOND"), help="Считать внутреннюю орбиту двух тел отдельно; DOP853")
    new.add_argument("--rotation", choices=["none", "lunar-solid"], default="none",
                     help="Начальное свободное вращение rigid-solid Луны: Newton/DOP853/per-body, без заданных фигур")
    new.add_argument("--quaternion-atol", type=float, help="Абсолютный допуск q для динамического вращения")
    new.add_argument("--spin-atol", type=float, help="Абсолютный допуск S, кг м²/с")
    new.add_argument("--eccentricity",type=float,default=0)
    new.add_argument("--contact-mode",choices=["stop","bounce","merge"])
    new.add_argument("--restitution",type=float,default=1)
    run = commands.add_parser("run",help="Продолжить контрольную точку")
    run.add_argument("input")
    run.add_argument("output")
    run.add_argument("--steps",type=int,required=True)
    run.add_argument("--backend",choices=["python","rust"])
    inspect = commands.add_parser("inspect",help="Диагностика контрольной точки")
    inspect.add_argument("input")
    convergence = commands.add_parser("converge",help="Verlet: сравнить шаги; DOP853: сравнить допуски на одном интервале")
    convergence.add_argument("input")
    convergence.add_argument("--steps",type=int,required=True)
    gui = commands.add_parser("gui",help="Открыть настольную лабораторию")
    gui.add_argument("input",nargs="?")
    orbit = commands.add_parser("fit-orbit", help="Восстановить орбиту по ранним угловым наблюдениям и проверить поздние")
    orbit.add_argument("input", help="Оптические наблюдения и фоновые эфемериды JSON")
    orbit.add_argument("output", help="Отчёт о подборе и отдельном прогнозе JSON")
    orbit.add_argument("--max-evaluations", type=int, default=150)
    orbit.add_argument("--night-systematic", type=float, default=None,
                       help="Общая ошибка станции за UTC-ночь, угловые секунды; по умолчанию из набора")
    args = parser.parse_args(argv)
    try:
        if args.command == "fit-orbit":
            from .orbit_determination import fit_dataset
            result = fit_dataset(args.input, args.output, args.max_evaluations, args.night_systematic)
            print(json.dumps({key:result[key] for key in ('epoch_jd_tdb','fit','limitation')} |
                {'training_rms_arcsec':result['training']['rms_arcsec'],
                 'holdout_rms_arcsec':result['holdout']['rms_arcsec']},
                ensure_ascii=False, allow_nan=False, indent=2))
            return 0
        if args.command == "gui":
            from .app import launch
            experiment,snapshot = open_experiment(args.input) if args.input else (None,None)
            launch(experiment,parent_snapshot=snapshot)
            return 0
        if args.command == "new":
            experiment = preset(args.preset,backend=args.backend,eccentricity=args.eccentricity)
            from .oblateness import earth_j2, earth_moon_quadrupoles, solar_j2, sun_earth_moon_quadrupoles
            figures = earth_j2(experiment.bodies, experiment.origin) if args.figures == "earth-j2" else ()
            if args.figures in ("earth-q2", "earth-moon-q2"):
                figures = earth_moon_quadrupoles(experiment.bodies, experiment.origin, moon=args.figures=="earth-moon-q2")
            if args.figures == "solar-j2":
                figures = solar_j2(experiment.bodies,experiment.origin)
            if args.figures == "sun-earth-moon-q2":
                figures = sun_earth_moon_quadrupoles(experiment.bodies,experiment.origin)
            experiment = replace(experiment,settings=Settings(args.dt if args.dt is not None else experiment.settings.dt,
                args.backend,args.contact_mode or experiment.settings.contact_mode,args.restitution,
                args.integrator or ("dop853" if args.physics == "eih-1pn" or figures or args.relative_pair or args.rotation != "none"
                    or (args.backend == "python" and not any(b.radius > 0 for b in experiment.bodies)) else "verlet"),
                args.rtol,args.position_atol,args.velocity_atol,args.physics,figures,
                tuple(args.relative_pair) if args.relative_pair else None,args.error_control))
            if args.rotation == "lunar-solid":
                from .nbody_rotation import lunar_initial
                from .experiment import create_experiment
                rotations = lunar_initial(experiment.bodies, experiment.origin)
                rotation = rotations[0]
                if args.quaternion_atol is not None:
                    rotation = replace(rotation, quaternion_atol=args.quaternion_atol)
                if args.spin_atol is not None:
                    rotation = replace(rotation, momentum_atol=args.spin_atol)
                experiment = create_experiment(experiment.bodies, experiment.settings,
                    origin=experiment.origin, rotations=(rotation,))
            elif args.quaternion_atol is not None or args.spin_atol is not None:
                raise ValueError("Допуски q/S требуют --rotation lunar-solid")
            save(experiment,args.output)
        else:
            experiment,snapshot = open_experiment(args.input)
            if args.command == "converge":
                from .convergence import compare_steps
                print(json.dumps(compare_steps(experiment,args.steps),ensure_ascii=False,allow_nan=False,indent=2))
                return 0
            if args.command == "run":
                if args.backend:
                    experiment = replace(experiment,settings=replace(experiment.settings,backend=args.backend))
                experiment = advance(experiment,args.steps)
                save_experiment(experiment,args.output,parent_snapshot=snapshot)
        print(json.dumps(report(experiment),ensure_ascii=False,allow_nan=False,indent=2))
    except (ValueError,RuntimeError,OSError,OverflowError) as error:
        parser.exit(2,f"Ошибка: {error}\n")
    return 0
