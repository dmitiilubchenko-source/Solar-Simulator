"""Fetch twenty sequential DE441 responses; freeze data before candidate residuals."""
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
from pathlib import Path
from time import perf_counter

import numpy as np

from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.assess_nominal_solar_packets import shared_epochs
from scripts.fixed_j2_year import inputs, jpl_vectors
from scripts.newton_year import ROOT, NAMES, hashes
from scripts.nominal_jpl import PROTOCOL, response, vectors
from solar_simulator.ephemerides import RESOLVED_IDS


def fetch_grid(output, cache, cached=False):
    output, cache = Path(output).resolve(), Path(cache).resolve()
    if (not output.is_relative_to(ROOT/'.tools') or not cache.is_relative_to(ROOT/'.tools')
            or output.exists()):
        raise ValueError('Use fresh output and project .tools cache')
    output.parent.mkdir(parents=True, exist_ok=True)
    seed, prior_times, *_ = inputs()
    times = epoch_grid()
    sources = hashes([PROTOCOL, 'scripts/nominal_jpl.py', 'scripts/fetch_ephemerides.py',
        'scripts/fetch_nominal_jpl.py', 'scripts/fixed_j2_year.py',
        'scripts/assess_edited_solar_packet20.py', 'scripts/assess_nominal_solar_packets.py'])
    report = dict(protocol=PROTOCOL, complete=False, checks_passed=False,
        source_sha256=sources, origin=asdict(seed.origin), units='SI', names=list(NAMES),
        ids=list(RESOLVED_IDS), epochs_seconds=times.tolist(), bodies=[],
        initial_dataset_changed=False, physical_parameters_fitted=False,
        fetched_after_free_integration=True, requests_sequential=True)
    start = perf_counter()

    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')

    save()
    try:
        # Verify old data through its pinned raw-response/parser lineage as well.
        old, _, old_hashes = jpl_vectors(seed, prior_times, ROOT/'.tools/qualification144/jpl-batches')
        report['old_raw_sha256'] = old_hashes
        _, a, b = shared_epochs(times, prior_times)
        for index, (name, body_id) in enumerate(zip(NAMES, RESOLVED_IDS)):
            rows, requests = [], []
            for kind, grid, suffix in [('regular', times[:-1], 'regular'), ('jd', times[-1:], 'final')]:
                file = f'raw/horizons-{body_id}-{suffix}.json'
                part, record = response(cache/file, body_id, grid, kind, cached=cached)
                rows.extend(part)
                requests.append(dict(record, file=file, kind=kind, epochs_seconds=grid.tolist()))
                print(name, suffix, len(part), 'validated', flush=True)
            values = vectors(rows)
            position = float(np.linalg.norm(values[a, :3]-old[b, index, :3], axis=1).max())
            velocity = float(np.linalg.norm(values[a, 3:]-old[b, index, 3:], axis=1).max())
            row = dict(name=name, id=body_id, states=rows, requests=requests,
                overlap_position_metres=position, overlap_velocity_m_per_s=velocity,
                overlap_passed=bool(position < .01 and velocity < 1e-8))
            report['bodies'].append(row)
            save()
            if not row['overlap_passed']:
                raise ValueError('Prior JPL overlap failed: '+name)
        if hashes(sources) != sources or hashes(old_hashes) != old_hashes:
            raise ValueError('Frozen source or old data changed')
        report.update(complete=True, checks_passed=True, completed_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        raise
    finally:
        report['wall_seconds'] = perf_counter()-start
        save()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--cached', action='store_true')
    args = parser.parse_args()
    fetch_grid(args.output, args.cache, args.cached)


if __name__ == '__main__':
    main()
