"""Командная строка лаборатории: создание, продолжение, отчёт и интерфейс."""
import argparse
from dataclasses import replace
import json

from .diagnostics import angular_momentum
from .experiment import PRESETS, Settings, advance, preset
from .simulation import total_energy, total_momentum, center_of_mass
from .storage import load, save


def report(experiment):
    initial = total_energy(experiment.initial)
    energy = total_energy(experiment.bodies)
    def vector(value):
        return [value.x,value.y,value.z]
    return dict(time_seconds=experiment.time,bodies=len(experiment.bodies),
        events=len(experiment.events),halted=experiment.halted,energy_joules=energy,
        dissipated_energy_joules=experiment.dissipated_energy,
        model_energy_offset_joules=experiment.model_energy_offset,
        energy_budget_residual_joules=energy+experiment.dissipated_energy+experiment.model_energy_offset-initial,
        momentum=vector(total_momentum(experiment.bodies)),
        angular_momentum=vector(angular_momentum(experiment.bodies)),
        center_of_mass=vector(center_of_mass(experiment.bodies)))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Solar Simulator — ньютоновская лаборатория (SI)")
    commands = parser.add_subparsers(dest="command",required=True)
    new = commands.add_parser("new",help="Создать сценарий JSON")
    new.add_argument("preset",choices=PRESETS)
    new.add_argument("output")
    new.add_argument("--backend",choices=["python","rust"],default="python")
    new.add_argument("--dt",type=float)
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
    convergence = commands.add_parser("converge",help="Сравнить dt, dt/2, dt/4 на одном интервале")
    convergence.add_argument("input")
    convergence.add_argument("--steps",type=int,required=True)
    gui = commands.add_parser("gui",help="Открыть настольную лабораторию")
    gui.add_argument("input",nargs="?")
    args = parser.parse_args(argv)
    try:
        if args.command == "gui":
            from .app import launch
            launch(load(args.input) if args.input else None)
            return 0
        if args.command == "new":
            experiment = preset(args.preset,backend=args.backend,eccentricity=args.eccentricity)
            experiment = replace(experiment,settings=Settings(args.dt if args.dt is not None else experiment.settings.dt,
                args.backend,args.contact_mode or experiment.settings.contact_mode,args.restitution))
            save(experiment,args.output)
        else:
            experiment = load(args.input)
            if args.command == "converge":
                from .convergence import compare_steps
                print(json.dumps(compare_steps(experiment,args.steps),ensure_ascii=False,allow_nan=False,indent=2))
                return 0
            if args.command == "run":
                if args.backend:
                    experiment = replace(experiment,settings=replace(experiment.settings,backend=args.backend))
                experiment = advance(experiment,args.steps)
                save(experiment,args.output)
        print(json.dumps(report(experiment),ensure_ascii=False,allow_nan=False,indent=2))
    except (ValueError,RuntimeError,OSError,OverflowError) as error:
        parser.exit(2,f"Ошибка: {error}\n")
    return 0
