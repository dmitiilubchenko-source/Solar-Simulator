"""Annual edited Solar with actual 20-hour packet endpoints and frozen physics."""
import argparse
from pathlib import Path

import numpy as np

from scripts.assess_edited_solar_year import DURATION
from scripts.edited_solar_interval import run

PROTOCOL = 'docs/edited-solar-packet20-protocol.md'
PACKET_SECONDS = 72000.


def epoch_grid():
    return np.r_[np.arange(0., DURATION, PACKET_SECONDS), DURATION]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output, times=epoch_grid(), grid='regular', protocol=PROTOCOL,
        driver_sources=('scripts/assess_edited_solar_packet20.py', 'tests/test_edited_solar_packet20.py'))
    if not result['checks_passed']:
        raise RuntimeError('Packet20 annual criteria failed; all evidence retained')


if __name__ == '__main__':
    main()
