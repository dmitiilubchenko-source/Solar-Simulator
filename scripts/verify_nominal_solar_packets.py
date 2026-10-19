"""Verify actual nominal CLI/Tk packets, preserving calendar provenance."""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import numpy as np

from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.assess_sandbox_planets import states
from scripts.newton_year import ROOT, NAMES, hashes
from scripts.verify_edited_solar_cli import FIELDS, check_bits
from solar_simulator.storage import load, save, to_document


def calendar_snapshots(path, seed):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    times = epoch_grid()
    names = [body.name for body in seed.bodies]
    masses = [body.mass for body in seed.bodies]
    if len(rows) != len(times) * len(names) or seed.origin is None:
        raise ValueError('Incomplete nominal CSV or missing calendar origin')
    values = []
    for index, time in enumerate(times):
        packet = rows[index * len(names):(index + 1) * len(names)]
        expected_jd = seed.origin.epoch_jd_tdb + time / 86400
        if ([row['name'] for row in packet] != names
                or [float(row['mass_kg']) for row in packet] != masses
                or any(float(row['time_seconds']) != time
                    or float(row['epoch_jd_tdb']) != expected_jd
                    or float(row['orientation_work_joules']) != 0. for row in packet)):
            raise ValueError('Nominal CSV order/mass/time/calendar/work mismatch')
        values.append([[float(row[key]) for key in FIELDS] for row in packet])
    result = np.array(values, dtype=float)
    if result.shape != (440, len(names), 6) or not np.isfinite(result).all():
        raise ValueError('Nonfinite or malformed nominal CSV states')
    return result


def verified_receipt(path):
    path = Path(path).resolve()
    report = json.loads(path.read_bytes())
    if (not report['complete'] or not report['source_input_dependencies_unchanged']
            or not report['reference_passed'] or report['origin'] is None
            or report['names'] != list(NAMES)):
        raise ValueError('Require complete nominal evidence and qualified reference')
    for name in ('source_sha256', 'input_sha256', 'dependency_sha256'):
        if hashes(report[name]) != report[name]:
            raise ValueError('Nominal source/input/actual dependency changed')
    if hashes([path.with_suffix('.npz')]).popitem()[1] != report['npz_sha256']:
        raise ValueError('Nominal trajectory archive changed')
    np.testing.assert_array_equal(report['epochs_seconds'], epoch_grid())
    return report


def gui_worker(input_path, output, expected_npz):
    """Real Laboratory loading, futures, target, poll, recording and draw calls."""
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    seed = load(input_path)
    before = to_document(seed)
    if seed.origin is None:
        raise ValueError('Nominal GUI requires calendar provenance')
    times, values = [seed.time], [states(seed.bodies)]
    outcome = dict(complete=False, checks_passed=False, visible_window=False,
        event_loop_manually_polled=True, file_chooser_stubbed=True, physics_mocked=False,
        modal_errors_raised=True, mainloop_rendering_measured=False, origin=asdict(seed.origin))
    root = app = None
    start = perf_counter()
    try:
        with np.load(expected_npz, allow_pickle=False) as data:
            expected = data['legacy_rust'].copy()
        root = tk.Tk()
        root.withdraw()
        app = Laboratory(root)
        with patch('solar_simulator.app.filedialog.askopenfilename', return_value=str(input_path)):
            app._load()
        if to_document(app.experiment) != before or app.batch.get() != '20':
            raise ValueError('GUI input or packet default changed')
        app.target.set(str(epoch_grid()[-1]))
        with patch('solar_simulator.app.messagebox.showerror', side_effect=RuntimeError('GUI packet failed')):
            app._start_target()
            app._poll()
            check_bits(values[0], expected[0])
            for index, epoch in enumerate(epoch_grid()[1:], 1):
                if app.future is None:
                    raise ValueError('GUI did not submit the actual worker')
                app.future.result(timeout=120)
                app._poll()
                if (app.experiment.time != epoch or app.experiment.settings != seed.settings
                        or app.experiment.origin != seed.origin):
                    raise ValueError('GUI epoch/settings/calendar changed')
                value = states(app.experiment.bodies)
                check_bits(value, expected[index])
                times.append(app.experiment.time)
                values.append(value)
                if index % 100 == 0:
                    print('nominal GUI packets', index, flush=True)
        if app.running or app.future is not None or app.target_time != epoch_grid()[-1]:
            raise ValueError('GUI failed to stop exactly at target')
        if to_document(seed) != before:
            raise ValueError('GUI input changed')
        save(app.experiment, output / 'final.json')
        outcome.update(complete=True, checks_passed=True, all_states_bitexact=True,
            samples=len(times), packets=len(times)-1, final_time_seconds=app.experiment.time)
    except BaseException as error:
        outcome['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if app is not None:
            app.close()
        elif root is not None:
            root.destroy()
        np.savez_compressed(output / 'states.npz', times=np.asarray(times), states=np.asarray(values))
        outcome['wall_seconds'] = perf_counter()-start
        outcome['output_sha256'] = hashes([p for p in output.iterdir() if p.is_file()])
        (output / 'receipt.json').write_text(json.dumps(outcome, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def run(output, annual_receipt):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / '.tools') or output.exists():
        raise ValueError('Use a fresh project .tools directory')
    report = verified_receipt(annual_receipt)
    packet_path = Path(annual_receipt).resolve().with_suffix('.npz')
    source = ROOT / 'docs/solar-sandbox-strict-checkpoint.json'
    seed = load(source)
    before = to_document(seed)
    if report['origin'] != asdict(seed.origin) or report['settings'] != json.loads(json.dumps(asdict(seed.settings))):
        raise ValueError('Nominal packet input/settings/calendar mismatch')
    sources = hashes(['scripts/verify_nominal_solar_packets.py', 'tests/test_nominal_solar_io.py',
        *('src/solar_simulator/'+n for n in ('app.py', 'continuous_cli.py', 'state_export.py', 'storage.py'))])
    bindings = hashes([annual_receipt, packet_path, source])
    output.mkdir(parents=True)
    result = dict(complete=False, checks_passed=False, scientific_scope_qualified=False,
        source_sha256=sources, input_sha256=bindings, numerical_scope_qualified=report['checks_passed'],
        physics_mocked=False, runtime_modified=False, general_release=False)

    def persist():
        (output / 'receipt.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8')

    persist()
    try:
        with np.load(packet_path, allow_pickle=False) as data:
            check_bits(data['initial'], states(seed.bodies))
            cli_dir = output / 'cli'
            command = [sys.executable, '-X', 'utf8', '-B', '-m', 'solar_simulator.continuous_cli',
                '--input', str(source), '--target', str(epoch_grid()[-1]), '--packet-steps', '20', '--output', str(cli_dir)]
            with (output / 'cli.log').open('x', encoding='utf-8') as stream:
                process = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
            if process.returncode:
                raise RuntimeError('Actual nominal CLI failed')
            cli = json.loads((cli_dir / 'receipt.json').read_bytes())
            if (cli['status'] != 'complete' or cli['packet_steps'] != 20 or cli['packets'] != 439
                    or cli['csv_rows'] != 4400 or not cli['experimental']
                    or cli['automatically_scientifically_qualified'] or cli['controller_buffers_saved']
                    or cli['origin'] != asdict(seed.origin) or cli['settings'] != report['settings']
                    or cli['units'] != 'SI' or cli['input_sha256'] != bindings[str(source)]):
                raise ValueError('CLI settings/calendar/execution/qualification contract changed')
            np.testing.assert_array_equal(cli['sample_times_seconds'], epoch_grid())
            if set(cli['output_sha256']) != {'initial.json', 'snapshots.csv', 'final.json', 'final.csv'}:
                raise ValueError('CLI output set changed')
            for name, digest in cli['output_sha256'].items():
                if hashes([cli_dir / name]).popitem()[1] != digest:
                    raise ValueError('CLI output SHA changed')
            if to_document(load(cli_dir / 'initial.json')) != before:
                raise ValueError('CLI initial state differs')
            check_bits(calendar_snapshots(cli_dir / 'snapshots.csv', seed), data['continuous_rust'])
            result['cli'] = dict(command=command, receipt=cli, checks_passed=True, all_states_bitexact=True)
            gui_dir = output / 'gui'
            command = [sys.executable, '-X', 'utf8', '-B', '-m', 'scripts.verify_nominal_solar_packets',
                'gui-worker', '--input', str(source), '--output', str(gui_dir), '--expected', str(packet_path)]
            with (output / 'gui.log').open('x', encoding='utf-8') as stream:
                process = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, timeout=1800)
            if process.returncode:
                raise RuntimeError('Actual nominal Tk worker failed')
            gui = json.loads((gui_dir / 'receipt.json').read_bytes())
            if (not gui['complete'] or not gui['checks_passed'] or gui['samples'] != 440
                    or gui['packets'] != 439 or gui['origin'] != report['origin']):
                raise ValueError('GUI incomplete or calendar changed')
            for name, digest in gui['output_sha256'].items():
                if hashes([Path(name)]).popitem()[1] != digest:
                    raise ValueError('GUI output SHA changed')
            with np.load(gui_dir / 'states.npz', allow_pickle=False) as snapshots:
                np.testing.assert_array_equal(snapshots['times'], epoch_grid())
                check_bits(snapshots['states'], data['legacy_rust'])
            for mode, directory in (('continuous_rust', cli_dir), ('legacy_rust', gui_dir)):
                final = load(directory / 'final.json')
                check_bits(states(final.bodies), data[mode][-1])
                if final.time != epoch_grid()[-1] or final.settings != seed.settings or final.origin != seed.origin:
                    raise ValueError('Final JSON epoch/settings/calendar changed')
            result['gui'] = dict(command=command, receipt=gui, checks_passed=True, all_states_bitexact=True)
        verified_receipt(annual_receipt)
        if hashes(sources) != sources or hashes(bindings) != bindings or to_document(seed) != before:
            raise ValueError('Operational source/input changed')
        result.update(complete=True, checks_passed=True, scientific_scope_qualified=report['checks_passed'],
            source_inputs_dependencies_unchanged=True,
            output_sha256=hashes([p for p in output.rglob('*') if p.is_file() and p != output / 'receipt.json']))
        persist()
    except BaseException as error:
        result['failure'] = dict(type=type(error).__name__, message=str(error))
        persist()
        raise
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode', required=True)
    gui = commands.add_parser('gui-worker')
    for name in ('input', 'output', 'expected'):
        gui.add_argument('--'+name, type=Path, required=True)
    audit = commands.add_parser('audit')
    for name in ('output', 'annual-receipt'):
        audit.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'gui-worker':
        gui_worker(args.input, args.output, args.expected)
    else:
        result = run(args.output, args.annual_receipt)
        print('nominal actual CLI/Tk bitexact', result['checks_passed'], flush=True)


if __name__ == '__main__':
    main()
