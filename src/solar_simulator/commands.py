"""Sandbox commands alongside the byte-frozen historical CLI diagnostics."""
import argparse
import json
from pathlib import Path
import sys

from . import cli
from .storage import save
from .time_control import advance_towards, validate_target
from .branch_io import open_experiment, parent_experiment, save_experiment


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    names={"run-until","solar-sandbox","branch","export-state","record-trajectory","view-trajectory",
           "compare-trajectories","view-comparison","check-recipe","replay-trajectory","inspect"}
    if argv and argv[0] not in names and argv[0] not in ("--help","-h"):
        return cli.main(argv)
    parser=argparse.ArgumentParser(description="Solar Simulator — песочница (SI)",
        epilog="Прежние команды: new, run, inspect, converge, gui, fit-orbit; COMMAND --help для параметров.")
    commands=parser.add_subparsers(dest="command",required=True)
    inspect=commands.add_parser('inspect',help='Диагностика checkpoint; --reliability объясняет модель и ограничения точности')
    inspect.add_argument('input')
    inspect.add_argument('--reliability',action='store_true',help='Opt-in: добавить numerical_reliability без интегрирования и оценки глобальной ошибки')
    run=commands.add_parser("run-until",help="Рассчитать вперёд до секунд от начала")
    run.add_argument("input");run.add_argument("output")
    run.add_argument("--time",type=float,required=True)
    run.add_argument("--batch",type=int,default=20)
    record=commands.add_parser('record-trajectory',help='Записать полные снимки завершённых пакетов в новую папку')
    record.add_argument('input');record.add_argument('output')
    record.add_argument('--time',type=float,required=True)
    record.add_argument('--batch',type=int,default=20,help='Численный пакет; не скорость просмотра')
    view=commands.add_parser('view-trajectory',help='Просмотр готовой траектории без расчёта')
    view.add_argument('input')
    audit=commands.add_parser('check-recipe',help='Проверить происхождение записи и совместимость окружения')
    audit.add_argument('input')
    audit.add_argument('--reliability',action='store_true',help='Opt-in: показать проверенную историю пакетов и границы научных утверждений')
    replay=commands.add_parser('replay-trajectory',help='Повторить те же пакеты в новый каталог и сравнить все кадры')
    replay.add_argument('input');replay.add_argument('output')
    compare=commands.add_parser('compare-trajectories',help='Сравнить parent/child на точных общих эпохах (JSON)')
    compare.add_argument('parent');compare.add_argument('child');compare.add_argument('output')
    compare.add_argument('--event-side',choices=('before','after'),required=True)
    compare.add_argument('--reference',help='Вычесть это тело отдельно в каждом опыте; иначе инерциальная')
    compare_view=commands.add_parser('view-comparison',help='Наложение записанных parent/child и Δr/Δv')
    compare_view.add_argument('parent');compare_view.add_argument('child')
    compare_view.add_argument('--event-side',choices=('before','after'),required=True)
    solar=commands.add_parser("solar-sandbox",help="10 тел EIH+fixedJ2: выбор Standard/Strict")
    solar.add_argument("output");solar.add_argument("--backend",choices=("python","rust"),default="python")
    solar.add_argument('--profile',choices=('standard','strict'),default='standard',
        help='Standard сохраняет прежний default; Strict — настройки исторической проверки года/пакета20')
    branch=commands.add_parser("branch",help="Извлечь parent/child из сохранённой ветки")
    branch.add_argument("input");branch.add_argument("output")
    branch.add_argument("--part",choices=("parent","child"),required=True)
    export=commands.add_parser("export-state",help="Орбитальный CSV-срез с SI и происхождением")
    export.add_argument("input");export.add_argument("output")
    args=parser.parse_args(argv)
    try:
        if args.command=='inspect':
            experiment,_=open_experiment(args.input)
            if args.reliability:
                from .inspection import report
                values=report(experiment)
            else:values=cli.report(experiment)
            print(json.dumps(values,ensure_ascii=False,allow_nan=False,indent=2))
            return 0
        if args.command=='check-recipe':
            from .recipe import audit_recipe
            from .trajectory import Trajectory
            track=Trajectory(args.input)
            if args.reliability:
                from .inspection import recipe_report
                result=recipe_report(track)
            else:result=audit_recipe(track)
            print(json.dumps(result,ensure_ascii=False,allow_nan=False))
            return 0 if result['compatible'] else 1
        if args.command=='replay-trajectory':
            from .recipe import replay_trajectory
            result=replay_trajectory(args.input,args.output)
            print(json.dumps(result,ensure_ascii=False,allow_nan=False))
            return 0 if result['reproduced_prefix'] else 1
        if args.command=='view-comparison':
            from .comparison_view import launch
            launch(args.parent,args.child,event_side=args.event_side)
            return 0
        if args.command=='compare-trajectories':
            from .comparison import Comparison
            from .trajectory import Trajectory
            comparison=Comparison(Trajectory(args.parent),Trajectory(args.child),event_side=args.event_side)
            comparison.save_report(args.output,reference=args.reference)
            print(json.dumps(dict(matched_epochs=len(comparison.pairs),output=str(Path(args.output).resolve())),
                             ensure_ascii=False,allow_nan=False))
            return 0
        if args.command=='view-trajectory':
            from .trajectory_view import launch
            launch(args.input)
            return 0
        snapshot=None
        if args.command=="solar-sandbox":
            from .solar_profiles import solar_sandbox
            experiment=solar_sandbox(profile=args.profile,backend=args.backend)
        else:
            if Path(args.input).resolve()==Path(args.output).resolve():
                raise ValueError("Выходной файл должен отличаться от входного; исходный опыт сохраняется")
            experiment,snapshot=open_experiment(args.input)
            if args.command=='record-trajectory':
                from .trajectory import record_trajectory
                try:
                    result=record_trajectory(experiment,args.output,args.time,packet_steps=args.batch,parent_snapshot=snapshot)
                except KeyboardInterrupt as error:
                    print('\n'.join(getattr(error,'__notes__',('Запись прервана',))),file=sys.stderr,flush=True)
                    return 130
                print(json.dumps(result,ensure_ascii=False,allow_nan=False))
                return 0
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
            return _run_until(experiment,snapshot,args)
        values=cli.report(experiment)
        if args.command=='solar-sandbox':
            from .solar_profiles import profile_scope
            values['solar_profile']=profile_scope(experiment)
        save_experiment(experiment,args.output,parent_snapshot=snapshot)
        print(json.dumps(values,ensure_ascii=False,allow_nan=False,indent=2))
    except (ValueError,RuntimeError,OSError,OverflowError,ImportError) as error:
        parser.exit(2,f"Ошибка: {error}\n")
    return 0


def _run_until(experiment, snapshot, args):
    """Protect both propagation and the final commit of its completed result."""
    try:
        while experiment.time < args.time and not experiment.halted:
            experiment=advance_towards(experiment,args.time,args.batch)
        values=cli.report(experiment)
        values.update(requested_target_seconds=args.time,target_reached=experiment.time==args.time)
        save_experiment(experiment,args.output,parent_snapshot=snapshot)
    except (KeyboardInterrupt,Exception) as error:
        from .recovery import save_recovery
        interrupted=isinstance(error,KeyboardInterrupt)
        reason='interrupted' if interrupted else 'failed'
        fallback_error=None
        try:
            path=save_recovery(experiment,parent_snapshot=snapshot,
                               directory=Path(args.output).resolve().parent,reason=reason)
        except (OSError,ValueError,RuntimeError,OverflowError) as first:
            fallback_error=str(first)
            try:
                path=save_recovery(experiment,parent_snapshot=snapshot,reason=reason)
            except (OSError,ValueError,RuntimeError,OverflowError) as second:
                raise OSError(f'Ошибка: {error}; recovery рядом с output: {first}; '
                              f'локальная recovery также не сохранена: {second}') from second
        diagnostic=dict(status=reason,recovery_path=str(path),
                        last_committed_time_seconds=experiment.time,
                        requested_target_seconds=args.time,target_reached=experiment.time==args.time,
                        recovery_fallback=fallback_error is not None)
        if fallback_error is not None:diagnostic['primary_recovery_error']=fallback_error
        print(json.dumps(diagnostic,ensure_ascii=False,allow_nan=False),file=sys.stderr,flush=True)
        if interrupted:return 130
        raise
    print(json.dumps(values,ensure_ascii=False,allow_nan=False,indent=2))
    return 0
