"""Verify actual continuous CLI IO against the qualified annual regular states."""
import argparse
import csv
from dataclasses import asdict
import json
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import numpy as np

from scripts.assess_edited_solar import CASES, fixture
from scripts.assess_edited_solar_year import epoch_grid, DURATION
from scripts.assess_sandbox_planets import states
from scripts.edited_j2 import verify_branch
from scripts.newton_year import ROOT, hashes, NAMES
from solar_simulator.storage import save, load, to_document

PROTOCOL = 'docs/edited-solar-cli-six-protocol.md'
FIELDS = ('x_m','y_m','z_m','vx_m_s','vy_m_s','vz_m_s')


def read_snapshots(path, names, masses):
    with Path(path).open(encoding='utf-8', newline='') as stream:
        rows = list(csv.DictReader(stream))
    n = len(names)
    if not rows or len(rows) % n:
        raise ValueError('Incomplete CSV body packet')
    times, values = [], []
    for start in range(0, len(rows), n):
        packet = rows[start:start+n]
        time = float(packet[0]['time_seconds'])
        if (not np.isfinite(time) or [r['name'] for r in packet] != list(names)
                or [float(r['mass_kg']) for r in packet] != list(masses)
                or any(float(r['time_seconds']) != time or r['epoch_jd_tdb'] != ''
                    or float(r['orientation_work_joules']) != 0. for r in packet)):
            raise ValueError('CSV order/mass/time/origin/work mismatch')
        value = np.array([[float(r[key]) for key in FIELDS] for r in packet])
        if not np.isfinite(value).all():
            raise ValueError('Nonfinite CSV state')
        if times and time <= times[-1]:
            raise ValueError('CSV epochs must strictly increase')
        times.append(time)
        values.append(value)
    return np.array(times), np.array(values)


def check_bits(actual, expected):
    if actual.dtype != np.dtype('float64') or expected.dtype != np.dtype('float64'):
        raise ValueError('CLI bit comparison requires float64 states')
    np.testing.assert_array_equal(actual.view(np.uint64), expected.view(np.uint64))


def run(output, annual_receipt):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / '.tools') or output.exists():
        raise ValueError('Use a fresh project .tools directory')
    annual_receipt = Path(annual_receipt).resolve()
    annual = json.loads(annual_receipt.read_bytes())
    if not annual['complete'] or annual['grid'] != 'regular':
        raise ValueError('Require a complete annual regular receipt')
    for group in ('source_sha256','input_sha256','dependency_sha256'):
        if hashes(annual[group]) != annual[group]:
            raise ValueError('Annual source/input/actual dependency changed')
    if not all(annual['cases'][case]['candidates']['continuous_rust']['checks_passed'] for case in CASES):
        raise ValueError('Annual continuous candidate failed; do not claim CLI qualification')
    npz = annual_receipt.with_suffix('.npz')
    if hashes([npz]).popitem()[1] != annual['npz_sha256']:
        raise ValueError('Annual trajectory cache changed')
    inputs = hashes([annual_receipt, npz])
    sources = hashes([PROTOCOL,'scripts/verify_edited_solar_cli.py','tests/test_edited_solar_cli.py'])
    output.mkdir(parents=True, exist_ok=False)
    report = dict(protocol=PROTOCOL, input_sha256=inputs, source_sha256=sources, cases={}, complete=False,
        checks_passed=False, packet_steps=6, runtime_modified=False, generic_cli_qualification=False)

    def persist():
        (output / 'verification.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')

    persist()
    try:
        with np.load(npz, allow_pickle=False) as arrays:
            for case in CASES:
                parent, branch, _ = fixture(case)
                seed = branch.child
                before, provenance = to_document(parent), verify_branch(parent, branch)
                source = output / (case+'-input.json')
                save(seed, source)
                source_digest = hashes([source]).popitem()[1]
                destination = output / case
                log = output / (case+'.log')
                command = [sys.executable,'-X','utf8','-B','-m','solar_simulator.continuous_cli',
                    '--input',str(source),'--target',str(DURATION),'--packet-steps','6','--output',str(destination)]
                with log.open('x',encoding='utf-8') as stream:
                    start = perf_counter()
                    result = subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
                    elapsed = perf_counter()-start
                row = dict(command=command, returncode=result.returncode, wall_seconds=elapsed,
                    input_sha256=source_digest, provenance=provenance, checks_passed=False)
                report['cases'][case] = row
                persist()
                if result.returncode:
                    raise RuntimeError('Actual CLI failed: '+case)
                receipt = json.loads((destination/'receipt.json').read_bytes())
                if (receipt['status']!='complete' or receipt['packet_steps']!=6 or receipt['packets']!=1461
                        or receipt['csv_rows']!=14620 or not receipt['experimental']
                        or receipt['automatically_scientifically_qualified'] or receipt['controller_buffers_saved']
                        or receipt['origin'] is not None or receipt['units']!='SI'):
                    raise ValueError('CLI receipt contract mismatch')
                if receipt['settings'] != json.loads(json.dumps(asdict(seed.settings))):
                    raise ValueError('CLI settings changed')
                times, actual = read_snapshots(destination/'snapshots.csv', NAMES, [b.mass for b in seed.bodies])
                expected = arrays[case+'_continuous_rust']
                np.testing.assert_array_equal(times, epoch_grid('regular'))
                np.testing.assert_array_equal(times, receipt['sample_times_seconds'])
                check_bits(actual, expected)
                initial, final = load(destination/'initial.json'), load(destination/'final.json')
                check_bits(states(initial.bodies), expected[0])
                check_bits(states(final.bodies), expected[-1])
                if final.time!=DURATION or initial.settings!=seed.settings or final.settings!=seed.settings:
                    raise ValueError('CLI final time or settings changed')
                for name,digest in receipt['output_sha256'].items():
                    if hashes([destination/name]).popitem()[1]!=digest:
                        raise ValueError('CLI output changed')
                if hashes([source]).popitem()[1]!=source_digest or to_document(parent)!=before or verify_branch(parent,branch)!=provenance:
                    raise ValueError('Input/parent/child changed')
                row.update(checks_passed=True, all_csv_states_bitexact=True, final_json_bitexact=True,
                    samples=len(times), receipt=receipt, output_sha256=hashes([log,destination/'receipt.json',source]))
                persist()
        if hashes(inputs)!=inputs or hashes(sources)!=sources:
            raise ValueError('CLI verification sources/inputs changed')
        for group in ('source_sha256','input_sha256','dependency_sha256'):
            if hashes(annual[group])!=annual[group]:
                raise ValueError('Scientific dependency changed during CLI')
        report.update(complete=True, checks_passed=all(r['checks_passed'] for r in report['cases'].values()),
            source_inputs_dependencies_unchanged=True)
        persist()
    except BaseException as error:
        report['failure']=dict(type=type(error).__name__,message=str(error))
        persist()
        raise
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--annual-receipt',type=Path,required=True)
    args=parser.parse_args()
    if not run(args.output,args.annual_receipt)['checks_passed']:
        raise RuntimeError('CLI verification failed; outputs retained')
    print('Actual CLI: three annual runs, all CSV and final JSON states bitexact', flush=True)


if __name__=='__main__':main()
