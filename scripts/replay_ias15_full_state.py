"""Offline basic pilot replay: no REBOUND import, binary load or integration."""
import argparse
import base64
import json
from pathlib import Path
import struct

import numpy as np

from scripts.assess_ias15 import metrics
from scripts.assess_ias15_restart import load_cases
from scripts.ias15_full_state import parse, numeric_fields, sha, PREFIX, BUFFERS, DP7, SCALARS, FullSnapshot
from scripts.ias15_restart import bits, restore
from scripts.kepler_transport import ROOT

REPORT = 'docs/ias15-full-state-validation.json'
ARRAYS = 'docs/ias15-full-state-samples.npz'


def replay(root=ROOT):
    root = Path(root)
    report = json.loads((root/REPORT).read_bytes())
    if (not report['complete'] or not report['pilot_passed'] or report['guards_only']
            or report['runtime_modified'] or report['production_eligible']
            or report['case'] != 'holdout_circular'):
        raise ValueError('Not a completed basic circular pilot')
    for name, digest in (report['source_sha256'] | report['input_sha256']).items():
        if sha((root/name).read_bytes()) != digest:
            raise ValueError('Changed full-state source/input: '+name)
    if sha((root/ARRAYS).read_bytes()) != report['array_archive_sha256']:
        raise ValueError('Full-state array archive SHA mismatch')
    case = load_cases(root)[0]['holdout_circular']
    if report['request'] != case['request'] or report['origin'] != case['origin']:
        raise ValueError('Different original actual-IC request')
    with np.load(root/ARRAYS, allow_pickle=False) as archive:
        data = {n: archive[n].copy() for n in archive.files}
    with np.load(root/'docs/ias15-restart-samples.npz', allow_pickle=False) as archive:
        old = {n: archive[n].copy() for n in archive.files if n.startswith('holdout_circular__')}
    if bits(data['times']) != bits(case['times']):
        raise ValueError('Changed epoch grid')
    expected = [(v[:3], v[3:]) for v in case['expected']]
    if not np.array_equal(data['oracle100'], np.asarray([[str(v) for v in row] for row in case['expected']])):
        raise ValueError('Changed independent actual-IC oracle')
    packets, snapshots = 0, 0
    for epsilon in ('1e-09', '1e-11'):
        row = report['results'][epsilon]
        if not row['pilot_passed'] or not row['previous353_warm_cold_bitexact']:
            raise ValueError('Pilot or previous353 gate false')
        prefix = epsilon+'__'
        def get(key):
            return data[prefix+key]
        ends = get('packet_endpoints')
        if bits(ends) != bits(old['holdout_circular__'+epsilon+'__warm__packet_endpoints']):
            raise ValueError('Changed packet boundaries')
        stats = row['statistics']
        if (stats['packets'] != len(ends)-1 or stats['restored_snapshots'] != len(ends)-1
                or stats['raw_c_masks'] != [[0, 0]]*(len(ends)-1)
                or stats['ias15_written_fields'] != 17 or stats['N_allocated'] != 6
                or not stats['all_packet_fields_bitexact'] or not stats['all_restored_fields_bitexact']):
            raise ValueError('Invalid restore metadata')
        for mode, previous in (('warm', 'warm'), ('full', 'warm'), ('cold', 'every-packet')):
            values = get(mode)
            if bits(values) != bits(old['holdout_circular__'+epsilon+'__'+previous+'__values']):
                raise ValueError('Previous353 output differs: '+mode)
            if metrics(case['seed'], case['times'], values, expected) != row['metrics'][mode]:
                raise ValueError('Independent metrics differ: '+mode)
        if not all(row['metrics'][mode]['checks_passed'] for mode in ('warm', 'full')):
            raise ValueError('Independent analytic/invariant gate failed')
        for index, epoch in enumerate(ends):
            saved = []
            for mode in ('warm', 'full'):
                binaries, physicals = get(mode+'_binary_base64'), get(mode+'_physical_json')
                if len(binaries) != len(ends) or len(physicals) != len(ends):
                    raise ValueError('Incomplete packet archive')
                raw = base64.b64decode(str(binaries[index]), validate=True)
                text = str(physicals[index])
                time, masses, state = restore(text, sha(text.encode()), case['origin'])
                if bits(time) != bits(epoch) or bits(masses) != bits(case['request']['masses']):
                    raise ValueError('Physical packet time/mass differs')
                if bits(state) != bits(get('packet_states')[index]):
                    raise ValueError('Physical packet state differs')
                header, fields = parse(raw)
                if not header.startswith(b'REBOUND Binary File. Version: 5.2.2\0'):
                    raise ValueError('Wrong binary version')
                if fields['t'] != struct.pack('=d', time) or len(fields['particles']) != 224:
                    raise ValueError('Wrong binary epoch/particle size')
                for i in range(2):
                    components = struct.unpack_from('=11d', fields['particles'], i*112)
                    if bits(components[:6]) != bits(state[i]) or bits(components[9]) != bits(masses[i]):
                        raise ValueError('Binary/physical packet differs')
                if index:
                    if len([k for k in fields if k.startswith(PREFIX)]) != 17:
                        raise ValueError('Incomplete IAS15 field set')
                    for k in BUFFERS:
                        if len(fields[PREFIX+k]) != 48*(7 if k in DP7 else 1):
                            raise ValueError('Wrong IAS15 allocation: '+k)
                    if any(PREFIX+k not in fields for k in SCALARS):
                        raise ValueError('Missing IAS15 scalar')
                # Only binary is needed for this pure-Python field comparison.
                saved.append(FullSnapshot(raw, '', '', '', '', '', '', '', ()))
                snapshots += 1
            if numeric_fields(saved[0], independent_control=True) != numeric_fields(saved[1], independent_control=True):
                raise ValueError('Archived warm/full fields differ')
        packets += len(ends)-1
        guards = row['guards']
        if len(guards) != 56 or len({g['name'] for g in guards}) != 56:
            raise ValueError('Missing/duplicate negative guards')
        if not all(g.get('rejected_before_c') or g.get('rejected_before_export') or g.get('rejected') for g in guards):
            raise ValueError('A negative guard failed')
    return dict(cases=1, variants=2, packets=packets, archived_warm_full_snapshots=snapshots,
                arrays=len(data), full_warm_bitexact=True, independent_metrics_reproduced=True,
                previous353_warm_cold_bitexact=True, runtime_modified=False,
                scope='offline evidence replay; no new C restore or numerical integration')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    print(json.dumps(replay(parser.parse_args().root), indent=2))


if __name__ == '__main__':
    main()
