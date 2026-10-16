"""Sandbox commands alongside the byte-frozen historical CLI diagnostics."""
import argparse
import json
from pathlib import Path
import sys

from . import cli
from .storage import save
from .time_control import advance_towards, validate_target
from .branch_io import open_experiment, parent_experiment


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    names={"run-until","solar-sandbox","branch","export-state"}
    if argv and argv[0] not in names and argv[0] not in ("--help","-h"):
        return cli.main(argv)
    parser=argparse.ArgumentParser(description="Solar Simulator — песочница (SI)",
        epilog="Прежние команды: new, run, inspect, converge, gui, fit-orbit; COMMAND --help для параметров.")
    commands=parser.add_subparsers(dest="command",required=True)
    run=commands.add_parser("run-until",help="Рассчитать вперёд до секунд от начала")
    run.add_argument("input");run.add_argument("output")
    run.add_argument("--time",type=float,required=True)
    run.add_argument("--batch",type=int,default=20)
    solar=commands.add_parser("solar-sandbox",help="Готовый проверенный10body EIH+fixedJ2 профиль")
    solar.add_argument("output");solar.add_argument("--backend",choices=("python","rust"),default="python")
    branch=commands.add_parser("branch",help="Извлечь parent/child из сохранённой ветки")
    branch.add_argument("input");branch.add_argument("output")
    branch.add_argument("--part",choices=("parent","child"),required=True)
    export=commands.add_parser("export-state",help="Орбитальный CSV-срез с SI и происхождением")
    export.add_argument("input");export.add_argument("output")
    args=parser.parse_args(argv)
    try:
        if args.command=="solar-sandbox":
            from .application_profiles import solar_sandbox
            experiment=solar_sandbox(backend=args.backend)
        else:
            if Path(args.input).resolve()==Path(args.output).resolve():
                raise ValueError("Выходной файл должен отличаться от входного; исходный опыт сохраняется")
            experiment,snapshot=open_experiment(args.input)
            if args.command=="export-state":
                from .state_export import export_state
                digest=export_state(experiment,args.output)
                print(json.dumps(dict(checkpoint_sha256=digest,bodies=len(experiment.bodies),
                                      time_seconds=experiment.time),ensure_ascii=False,allow_nan=False))
                return 0
            if args.command=="branch":
                if args.part=="parent":experiment=parent_experiment(snapshot)
                elif snapshot is None:raise ValueError("Для branch требуется файл ветки")
                values=cli.report(experiment);save(experiment,args.output)
                print(json.dumps(values,ensure_ascii=False,allow_nan=False,indent=2))
                return 0
            validate_target(experiment,args.time,args.batch)
            while experiment.time < args.time and not experiment.halted:
                experiment=advance_towards(experiment,args.time,args.batch)
        values=cli.report(experiment)
        if args.command=="run-until":
            values.update(requested_target_seconds=args.time,target_reached=experiment.time==args.time)
        save(experiment,args.output)
        print(json.dumps(values,ensure_ascii=False,allow_nan=False,indent=2))
    except (ValueError,RuntimeError,OSError,OverflowError) as error:
        parser.exit(2,f"Ошибка: {error}\n")
    return 0
