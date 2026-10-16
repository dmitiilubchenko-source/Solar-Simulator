"""Audit actual CLI/Tk packet paths and compare exact shared annual epochs."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import numpy as np

from scripts.assess_edited_solar import CASES, fixture
from scripts.assess_edited_solar_month import check_same_experiment
from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.assess_edited_solar_year import epoch_grid as six_grid, DURATION
from scripts.assess_sandbox_planets import states
from scripts.newton_year import ROOT, hashes, agreement, NAMES
from scripts.verify_edited_solar_cli import read_snapshots, check_bits
from solar_simulator.storage import load, save, to_document

PROTOCOL = 'docs/edited-solar-packet20-protocol.md'


def check_packet_boundaries(statistics):
    np.testing.assert_array_equal(statistics['packet_endpoints'], epoch_grid()[1:])
    if statistics['packets'] != 439 or not statistics['finished'] or statistics['failed']:
        raise ValueError('Wrong actual packet completion contract')


def shared_indices(packet_times, six_times):
    np.testing.assert_array_equal(packet_times, epoch_grid())
    np.testing.assert_array_equal(six_times, six_grid('regular'))
    common, a, b = np.intersect1d(packet_times, six_times, return_indices=True)
    if len(common) != 148:
        raise ValueError('Wrong exact shared epoch count')
    return common, a, b


def verified_input(path):
    path = Path(path).resolve()
    document = json.loads(path.read_bytes())
    if not document['complete'] or not document['source_input_dependencies_unchanged']:
        raise ValueError('Incomplete or inconsistent scientific receipt')
    for group in ('source_sha256', 'input_sha256', 'dependency_sha256'):
        if hashes(document[group]) != document[group]:
            raise ValueError('Scientific source/input/actual dependency changed: '+group)
    if hashes([path.with_suffix('.npz')]).popitem()[1] != document['npz_sha256']:
        raise ValueError('Scientific trajectory archive changed')
    if set(document['cases']) != set(CASES) or not all(r['reference_passed'] for r in document['cases'].values()):
        raise ValueError('Require all three complete qualified references')
    return document


def gui_worker(input_path, output, expected_npz, case):
    """Use real widgets, worker futures, _start_target and _poll; no force mocks."""
    import tkinter as tk
    from unittest.mock import patch
    from solar_simulator.app import Laboratory

    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    seed = load(input_path)
    before = to_document(seed)
    times, values = [seed.time], [states(seed.bodies)]
    outcome = dict(complete=False, checks_passed=False, visible_window=False,
        event_loop_manually_polled=True, file_chooser_stubbed=True,
        modal_errors_raised=True, physics_mocked=False, mainloop_rendering_measured=False, case=case)
    root = None
    app = None
    start = perf_counter()
    try:
        with np.load(expected_npz, allow_pickle=False) as data:
            expected = data[case+'_legacy_rust'].copy()
        root = tk.Tk()
        root.withdraw()
        app = Laboratory(root)
        with patch('solar_simulator.app.filedialog.askopenfilename', return_value=str(input_path)):
            app._load()
        if to_document(app.experiment) != before:
            raise ValueError('GUI JSON loading changed the input')
        if app.batch.get() != '20':
            raise ValueError('GUI default batch changed')
        app.target.set(str(DURATION))
        # A modal error must fail this unattended audit rather than await a click.
        with patch('solar_simulator.app.messagebox.showerror', side_effect=RuntimeError('GUI packet failed')):
            app._start_target()
            app._poll()
            check_bits(values[0], expected[0])
            for index, epoch in enumerate(epoch_grid()[1:], 1):
                if app.future is None:
                    raise ValueError('GUI failed to submit an actual worker')
                app.future.result(timeout=120)
                app._poll()
                if app.experiment.time != epoch or app.experiment.settings != seed.settings:
                    raise ValueError('GUI changed packet epoch or scientific settings')
                value = states(app.experiment.bodies)
                times.append(app.experiment.time)
                values.append(value)
                check_bits(value, expected[index])
                if index % 100 == 0:
                    print(case, 'GUI packets', index, flush=True)
        if app.running or app.future is not None or app.target_time != DURATION:
            raise ValueError('GUI did not stop exactly at its annual target')
        if to_document(seed) != before or app.experiment.origin is not None:
            raise ValueError('GUI input/provenance changed')
        save(app.experiment, output/'final.json')
        outcome.update(complete=True, checks_passed=True, samples=len(times), packets=len(times)-1,
            all_states_bitexact=True, final_time_seconds=app.experiment.time)
    except BaseException as error:
        outcome['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        if app is not None:
            app.close()
        elif root is not None:
            root.destroy()
        np.savez_compressed(output/'states.npz', times=np.asarray(times), states=np.asarray(values))
        outcome['wall_seconds'] = perf_counter()-start
        outcome['output_sha256'] = hashes([p for p in output.iterdir() if p.is_file()])
        (output/'receipt.json').write_text(json.dumps(outcome, indent=2, allow_nan=False)+'\n', encoding='utf-8')


def run(output, packet_receipt, six_receipt):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT/'.tools') or output.exists():
        raise ValueError('Use a fresh project .tools directory; preserve prior evidence')
    packet_path, six_path = Path(packet_receipt).resolve(), Path(six_receipt).resolve()
    packet, six = verified_input(packet_path), verified_input(six_path)
    sources = hashes([PROTOCOL, 'scripts/verify_edited_solar_packets.py', 'tests/test_edited_solar_packets.py'])
    inputs = hashes([packet_path, packet_path.with_suffix('.npz'), six_path, six_path.with_suffix('.npz')])
    output.mkdir(parents=True, exist_ok=False)
    report = dict(protocol=PROTOCOL, source_sha256=sources, input_sha256=inputs,
        complete=False, checks_passed=False, io_checks_passed=False, declared_scope_qualified=False,
        annual_original_checks_passed=packet['checks_passed'], cases={}, interpolation_used=False,
        runtime_modified=False, generic_cli_qualification=False, nominal_qualification=False,
        jpl_comparison=False, source_integrals_verified=False)

    def persist():
        (output/'verification.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')

    persist()
    try:
        with np.load(packet_path.with_suffix('.npz'), allow_pickle=False) as annual, np.load(six_path.with_suffix('.npz'), allow_pickle=False) as old:
            for case in CASES:
                parent, branch, _ = fixture(case)
                seed = branch.child
                before = to_document(parent)
                check_same_experiment(packet['cases'][case], six['cases'][case])
                check_bits(annual[case+'_initial'], states(seed.bodies))
                check_bits(annual[case+'_initial'], old[case+'_initial'])
                common, a, b = shared_indices(annual[case+'_times'], old[case+'_times'])
                for mode in ('legacy_python','legacy_rust','continuous_rust'):
                    check_packet_boundaries(packet['cases'][case]['candidates'][mode]['statistics'])
                row = dict(common_samples=len(common), common_epochs_seconds=common.tolist(),
                    shared_diagnostics={}, accuracy_by_mode={m:c['checks_passed'] for m,c in packet['cases'][case]['candidates'].items()})
                report['cases'][case] = row
                for mode in ('legacy_python','legacy_rust','continuous_rust','reference_2'):
                    actual, previous = annual[case+'_'+mode][a], old[case+'_'+mode][b]
                    row['shared_diagnostics'][mode] = dict(**agreement(actual, previous, list(NAMES)),
                        bitexact=bool(np.array_equal(actual.view(np.uint64), previous.view(np.uint64))))
                source = output/(case+'-input.json')
                save(seed, source)
                source_sha = hashes([source]).popitem()[1]
                cli_dir = output/(case+'-cli')
                command = [sys.executable,'-X','utf8','-B','-m','solar_simulator.continuous_cli',
                    '--input',str(source),'--target',str(DURATION),'--packet-steps','20','--output',str(cli_dir)]
                start = perf_counter()
                with (output/(case+'-cli.log')).open('x',encoding='utf-8') as stream:
                    result = subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=600)
                process_elapsed = perf_counter()-start
                if result.returncode:
                    raise RuntimeError('Actual CLI failed: '+case)
                receipt = json.loads((cli_dir/'receipt.json').read_bytes())
                if (receipt['status']!='complete' or receipt['packet_steps']!=20 or receipt['packets']!=439
                        or receipt['csv_rows']!=4400 or not receipt['experimental']
                        or receipt['automatically_scientifically_qualified'] or receipt['controller_buffers_saved']
                        or receipt['origin'] is not None or receipt['units']!='SI'
                        or receipt['settings'] != json.loads(json.dumps(asdict(seed.settings)))):
                    raise ValueError('CLI contract changed')
                if receipt['input_sha256'] != source_sha:
                    raise ValueError('CLI reported a different input')
                if set(receipt['output_sha256']) != {'initial.json','snapshots.csv','final.json','final.csv'}:
                    raise ValueError('CLI output set changed')
                for name, digest in receipt['output_sha256'].items():
                    if hashes([cli_dir/name]).popitem()[1] != digest:
                        raise ValueError('CLI output changed: '+name)
                times, actual = read_snapshots(cli_dir/'snapshots.csv', NAMES, [b.mass for b in seed.bodies])
                np.testing.assert_array_equal(times, epoch_grid())
                np.testing.assert_array_equal(times, receipt['sample_times_seconds'])
                check_bits(actual, annual[case+'_continuous_rust'])
                final = load(cli_dir/'final.json')
                check_bits(states(final.bodies), actual[-1])
                if final.time != DURATION or final.settings != seed.settings or final.origin is not None:
                    raise ValueError('CLI final state metadata changed')
                row['cli'] = dict(checks_passed=True, all_states_bitexact=True, receipt=receipt,
                    command=command, process_wall_seconds=process_elapsed)
                gui_dir = output/(case+'-gui')
                command = [sys.executable,'-X','utf8','-B','-m','scripts.verify_edited_solar_packets','gui-worker',
                    '--input',str(source),'--output',str(gui_dir),'--expected',str(packet_path.with_suffix('.npz')),'--case',case]
                with (output/(case+'-gui.log')).open('x',encoding='utf-8') as stream:
                    result = subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=1800)
                if result.returncode:
                    raise RuntimeError('Actual Tk worker failed: '+case)
                gui = json.loads((gui_dir/'receipt.json').read_bytes())
                if not gui['complete'] or not gui['checks_passed'] or gui['samples']!=440 or gui['packets']!=439:
                    raise ValueError('GUI receipt incomplete')
                with np.load(gui_dir/'states.npz',allow_pickle=False) as snapshots:
                    np.testing.assert_array_equal(snapshots['times'], epoch_grid())
                    check_bits(snapshots['states'], annual[case+'_legacy_rust'])
                check_bits(states(load(gui_dir/'final.json').bodies), annual[case+'_legacy_rust'][-1])
                row['gui'] = dict(command=command, receipt=gui, all_states_bitexact=True, checks_passed=True)
                if hashes([source]).popitem()[1]!=source_sha or to_document(parent)!=before:
                    raise ValueError('Input or parent changed during IO audit')
                row['output_sha256'] = hashes([p for p in output.rglob('*') if p.is_file() and (p.parent in (cli_dir,gui_dir) or p==source)])
                row['output_sha256'].update(hashes([output/(case+'-cli.log'),output/(case+'-gui.log')]))
                persist()
                print(case, 'actual CLI/Tk all 440 states bitexact', flush=True)
        if hashes(sources)!=sources or hashes(inputs)!=inputs:
            raise ValueError('Operational source/input changed')
        verified_input(packet_path)
        verified_input(six_path)
        report.update(complete=True, checks_passed=True, io_checks_passed=True,
            declared_scope_qualified=bool(packet['checks_passed']), source_inputs_dependencies_unchanged=True)
        persist()
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        persist()
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='mode',required=True)
    gui = commands.add_parser('gui-worker')
    for name in ('input','output','expected'):
        gui.add_argument('--'+name,type=Path,required=True)
    gui.add_argument('--case',choices=CASES,required=True)
    audit = commands.add_parser('audit')
    for name in ('output','packet-receipt','six-receipt'):
        audit.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    if args.mode=='gui-worker':
        gui_worker(args.input,args.output,args.expected,args.case)
    else:
        run(args.output,args.packet_receipt,args.six_receipt)


if __name__=='__main__':
    main()
