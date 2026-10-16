"""Exact-epoch comparison of the first quarter inside an annual edited run."""
import argparse
import json
from pathlib import Path

import numpy as np

from scripts.assess_edited_solar_year import epoch_grid as annual_grid
from scripts.assess_edited_solar_quarter import epoch_grid as quarter_grid
from scripts.assess_edited_solar_month import check_same_experiment, candidate_metrics
from scripts.assess_edited_solar import within
from scripts.newton_year import ROOT, hashes, agreement, NAMES

PROTOCOL = 'docs/edited-solar-year-protocol.md'


def matching_indices(annual, quarter, grid):
    np.testing.assert_array_equal(annual, annual_grid(grid))
    np.testing.assert_array_equal(quarter, quarter_grid(grid))
    common, ia, iq = np.intersect1d(annual, quarter, return_indices=True)
    expected = quarter if grid == 'regular' else quarter[:-1]
    np.testing.assert_array_equal(common, expected)
    if len(common) != 361:
        raise ValueError('Wrong shared epoch count')
    return common, ia, iq


def reference_metrics(actual, expected):
    result = agreement(actual, expected, list(NAMES))
    return dict(**result, checks_passed=bool(within(result['all_bodies'], 1., 1e-6)
        and within(result['moon_relative_to_earth'], .01, 1e-7)))


def same_bits(actual, expected):
    if actual.dtype != np.dtype('float64') or expected.dtype != np.dtype('float64'):
        raise ValueError('Prefix bit comparison requires float64 states')
    return bool(np.array_equal(actual.view(np.uint64), expected.view(np.uint64)))


def run(output, year_regular, year_shifted, quarter_regular, quarter_shifted):
    output = Path(output).resolve()
    if not output.is_relative_to(ROOT / '.tools'):
        raise ValueError('Audit output must be inside project .tools')
    if any(output.with_suffix(s).exists() for s in ('.json', '.npz')):
        raise ValueError('Preserve old prefix audit; use fresh output')
    output.parent.mkdir(parents=True, exist_ok=True)
    paths = {'regular': (Path(year_regular).resolve(), Path(quarter_regular).resolve()),
        'shifted': (Path(year_shifted).resolve(), Path(quarter_shifted).resolve())}
    public_path = ROOT / 'docs/edited-solar-quarter-validation.json'
    public = json.loads(public_path.read_bytes())
    input_paths = [public_path]
    for pair in paths.values():
        for path in pair:
            input_paths.extend((path, path.with_suffix('.npz')))
    inputs = hashes(input_paths)
    sources = hashes([PROTOCOL, 'scripts/assess_edited_solar_prefix.py', 'tests/test_edited_solar_prefix.py'])
    report = dict(protocol=PROTOCOL, input_sha256=inputs, source_sha256=sources,
        grids={}, complete=False, checks_passed=False, interpolation_used=False,
        runtime_modified=False, jpl_comparison=False, source_integrals_verified=False)
    index_arrays = {}

    def save():
        np.savez_compressed(output.with_suffix('.npz'), **index_arrays)
        report['npz_sha256'] = hashes([output.with_suffix('.npz')]).popitem()[1]
        output.with_suffix('.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n', encoding='utf-8')

    save()
    try:
        for grid, (year_path, quarter_path) in paths.items():
            annual = json.loads(year_path.read_bytes())
            quarter = json.loads(quarter_path.read_bytes())
            cases = {'sun_mass', 'earth_position', 'moon_velocity'}
            if set(annual['cases']) != cases or set(quarter['cases']) != cases:
                raise ValueError('All three declared edits must be included')
            # A complete but inaccurate candidate is still available for an honest
            # prefix comparison; do not turn the earlier accuracy failure into a pass.
            for path, document in ((year_path, annual), (quarter_path, quarter)):
                if not document['complete'] or document['grid'] != grid:
                    raise ValueError('Incomplete or mismatched input receipt')
                for group in ('source_sha256', 'input_sha256', 'dependency_sha256'):
                    if hashes(document[group]) != document[group]:
                        raise ValueError('Source/input/actual dependency changed: ' + str(path))
                if hashes([path.with_suffix('.npz')]).popitem()[1] != document['npz_sha256']:
                    raise ValueError('Input trajectory archive changed')
            if quarter != public['measurements'][grid]:
                raise ValueError('Quarter receipt differs from the published baseline')
            if hashes([quarter_path]).popitem()[1] != public['receipts'][grid]['json_sha256']:
                raise ValueError('Quarter receipt SHA differs')
            with np.load(year_path.with_suffix('.npz'), allow_pickle=False) as a:
                years = {k: a[k].copy() for k in a.files}
            with np.load(quarter_path.with_suffix('.npz'), allow_pickle=False) as q:
                quarters = {k: q[k].copy() for k in q.files}
            if not all(np.isfinite(v).all() for v in (*years.values(), *quarters.values())):
                raise ValueError('Nonfinite cached states')
            grid_row = dict(cases={}, annual_original_checks_passed=annual['checks_passed'])
            report['grids'][grid] = grid_row
            for case, year_row in annual['cases'].items():
                quarter_row = quarter['cases'][case]
                check_same_experiment(year_row, quarter_row)
                np.testing.assert_array_equal(years[case + '_initial'], quarters[case + '_initial'])
                common, ia, iq = matching_indices(years[case + '_times'], quarters[case + '_times'], grid)
                index_arrays[grid + '_' + case + '_times'] = common
                index_arrays[grid + '_' + case + '_annual_indices'] = ia
                index_arrays[grid + '_' + case + '_quarter_indices'] = iq
                row = dict(common_samples=len(common), last_common_seconds=float(common[-1]),
                    omitted_quarter_epochs_seconds=np.setdiff1d(quarters[case + '_times'], common).tolist(),
                    candidates={})
                grid_row['cases'][case] = row
                for mode in ('legacy_python', 'legacy_rust', 'continuous_rust', 'reference'):
                    suffix = '_reference_2' if mode == 'reference' else '_' + mode
                    av, qv = years[case + suffix], quarters[case + suffix]
                    if av.shape != (len(annual_grid(grid)), 10, 6) or qv.shape != (len(quarter_grid(grid)), 10, 6):
                        raise ValueError('Wrong cached trajectory shape')
                    av, qv = av[ia], qv[iq]
                    result = reference_metrics(av, qv) if mode == 'reference' else candidate_metrics(av, qv)
                    row['candidates'][mode] = dict(**result, bitexact=same_bits(av, qv),
                        bitexact_sample_count=int(np.all(av.view(np.uint64) == qv.view(np.uint64), axis=(1, 2)).sum()))
                save()
        if hashes(inputs) != inputs or hashes(sources) != sources:
            raise ValueError('Prefix audit inputs/source changed')
        report.update(complete=True, source_inputs_unchanged=True,
            checks_passed=all(c['checks_passed'] for g in report['grids'].values()
                for row in g['cases'].values() for c in row['candidates'].values()))
        save()
    except BaseException as error:
        report['failure'] = dict(type=type(error).__name__, message=str(error))
        save()
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'year-regular', 'year-shifted', 'quarter-regular', 'quarter-shifted'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output, args.year_regular, args.year_shifted, args.quarter_regular, args.quarter_shifted)
    if not result['checks_passed']:
        raise RuntimeError('Prefix criteria failed; receipts preserved')
    print('Prefix audit complete: 24 comparisons passed, exact shared epochs only', flush=True)


if __name__ == '__main__':
    main()
