"""One Julian year of edited Solar, using the frozen explicit-epoch runner."""
import argparse
from pathlib import Path

import numpy as np

from scripts.edited_solar_interval import run

PROTOCOL = 'docs/edited-solar-year-protocol.md'
DURATION = 31557600.


def epoch_grid(grid):
    if grid == 'regular':
        return np.arange(0., DURATION + 1., 21600.)
    if grid == 'shifted':
        return np.r_[0., np.arange(10800., DURATION, 21600.), DURATION]
    raise ValueError('Undeclared annual grid')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--grid', choices=('regular', 'shifted'), required=True)
    parser.add_argument('--regular-receipt', type=Path)
    args = parser.parse_args()
    result = run(args.output, times=epoch_grid(args.grid), grid=args.grid, protocol=PROTOCOL,
        driver_sources=('scripts/assess_edited_solar_year.py', 'tests/test_edited_solar_year.py'),
        regular_receipt=args.regular_receipt,
        regular_times=epoch_grid('regular') if args.grid == 'shifted' else None)
    if not result['checks_passed']:
        raise RuntimeError('Annual criteria failed; all receipts preserved')


if __name__ == '__main__':
    main()
