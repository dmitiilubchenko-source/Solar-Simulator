"""Reject wrong nominal calendar/CSV evidence and preserve prior IO outputs."""
import csv
from dataclasses import asdict
import json

import numpy as np
import pytest

from scripts.assess_edited_solar_packet20 import epoch_grid
from scripts.verify_edited_solar_cli import FIELDS
from scripts.verify_nominal_solar_packets import calendar_snapshots, verified_receipt, run
from solar_simulator.storage import load
from scripts.newton_year import ROOT


@pytest.mark.parametrize('corruption', [None, 'calendar', 'time', 'mass', 'order', 'missing', 'nan'])
def test_all_nominal_csv_epochs_and_metadata_are_checked(tmp_path, corruption):
    seed = load(ROOT / 'docs/solar-sandbox-strict-checkpoint.json')
    path = tmp_path / 'snapshots.csv'
    rows = []
    for time in epoch_grid():
        for body in seed.bodies:
            rows.append([time, seed.origin.epoch_jd_tdb + time/86400, body.name, body.mass, *([0.] * 7)])
    if corruption == 'calendar': rows[105][1] += .001
    if corruption == 'time': rows[105][0] += .001
    if corruption == 'mass': rows[105][3] *= 2
    if corruption == 'order': rows[105][2] = 'Earth'
    if corruption == 'missing': rows.pop()
    if corruption == 'nan': rows[105][4] = float('nan')
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['time_seconds', 'epoch_jd_tdb', 'name', 'mass_kg', *FIELDS, 'orientation_work_joules'])
        writer.writerows(rows)
    if corruption is None:
        assert calendar_snapshots(path, seed).shape == (440, 10, 6)
    else:
        with pytest.raises(ValueError): calendar_snapshots(path, seed)


@pytest.mark.parametrize('corruption', ['incomplete', 'reference', 'origin', 'source', 'archive'])
def test_nominal_receipt_rejects_untrusted_sources_or_missing_calendar(tmp_path, corruption):
    path = tmp_path / 'receipt.json'
    seed = load(ROOT / 'docs/solar-sandbox-strict-checkpoint.json')
    document = dict(complete=True, source_input_dependencies_unchanged=True, reference_passed=True,
        origin=asdict(seed.origin), names=[b.name for b in seed.bodies],
        source_sha256={}, input_sha256={}, dependency_sha256={}, npz_sha256='wrong')
    if corruption == 'incomplete': document['complete'] = False
    if corruption == 'reference': document['reference_passed'] = False
    if corruption == 'origin': document['origin'] = None
    if corruption == 'source': document['source_sha256'] = {str(path): 'wrong'}
    path.with_suffix('.npz').write_bytes(b'saved trajectory')
    path.write_text(json.dumps(document), encoding='utf-8')
    with pytest.raises(ValueError): verified_receipt(path)


def test_previous_operational_evidence_is_preserved_before_receipt_reads(monkeypatch, tmp_path):
    from scripts import verify_nominal_solar_packets as module
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    output = tmp_path / '.tools' / 'kept'
    output.mkdir(parents=True)
    marker = output / 'receipt.json'
    marker.write_bytes(b'retained IO failure')
    with pytest.raises(ValueError, match='fresh'): run(output, 'unused')
    assert marker.read_bytes() == b'retained IO failure'
